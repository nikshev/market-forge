"""What a run reports, and what it refuses to report (REQ-WP-010)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from channelflow.backtest import FORBIDDEN_ECONOMIC_FIELDS, BacktestReport, BacktestRunner
from channelflow.bars import Bar
from channelflow.channels import RollingOLSChannel
from channelflow.signals import CandidateState, SignalMachine


def _run(bars: list[Bar], **overrides: object) -> BacktestReport:
    machine = replace(SignalMachine(), **overrides)  # type: ignore[arg-type]
    return BacktestRunner(channel=RollingOLSChannel(lookback=60), machine=machine).run(bars)


@pytest.mark.trace("REQ-WP-010")
def test_candidates_are_counted_by_direction_and_boundary(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-007, SC-004."""
    report = _run(falling_with_breakouts)

    assert report.candidates_opened > 0
    assert sum(report.by_direction.values()) == report.candidates_opened
    assert sum(report.by_boundary.values()) == report.candidates_opened
    assert set(report.by_direction) <= {"long", "short"}
    assert set(report.by_boundary) <= {"upper", "lower", "middle"}


@pytest.mark.trace("REQ-WP-010")
def test_the_confirmation_rate_and_terminal_reasons_are_reported(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-008."""
    report = _run(falling_with_breakouts)

    assert report.confirmed == sum(
        1 for t in report.transitions if t.to_state is CandidateState.CONFIRMED
    )
    assert report.confirmation_rate == pytest.approx(report.confirmed / report.candidates_opened)
    assert report.terminal_reasons, "every candidate is still live, which the fixture forbids"
    assert all(reason.strip() for reason in report.terminal_reasons)


@pytest.mark.trace("REQ-WP-010")
def test_an_empty_run_reports_zeroes_rather_than_dividing_by_them() -> None:
    """The edge case named in the spec: no candidates is a result, not an error."""
    report = _run([])

    assert report.bars_replayed == 0
    assert report.candidates_opened == 0
    assert report.confirmation_rate == 0.0
    assert report.transitions == ()


@pytest.mark.trace("REQ-WP-010")
def test_bars_without_enough_history_are_reported_as_skipped(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-011, SC-006. 'No setups found' and 'we could never look' differ."""
    short = falling_with_breakouts[:40]
    report = _run(short)

    assert report.bars_skipped_no_channel == len(short)
    assert report.candidates_opened == 0

    full = _run(falling_with_breakouts)
    assert full.bars_skipped_no_channel == 59, "the lookback is 60; 59 bars precede the first fit"


@pytest.mark.trace("REQ-WP-010")
def test_the_report_covers_the_bars_event_time_range(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-010, SC-003's second half: the range comes from the data."""
    report = _run(falling_with_breakouts)

    assert report.bars_replayed == len(falling_with_breakouts)
    assert report.first_bar_close_ns == falling_with_breakouts[0].close_time_ns
    assert report.last_bar_close_ns == falling_with_breakouts[-1].close_time_ns


@pytest.mark.trace("REQ-WP-010")
def test_two_configurations_give_different_reports_and_each_names_its_own(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-009, SC-005."""
    default = _run(falling_with_breakouts)
    strict = _run(falling_with_breakouts, min_quality=0.9)

    assert strict.candidates_opened != default.candidates_opened
    assert default.configuration["min_quality"] == "0.5"
    assert strict.configuration["min_quality"] == "0.9"
    for key in (
        "channel_lookback",
        "zone_upper",
        "zone_lower",
        "zone_middle",
        "slope_threshold",
        "expiry_bars",
        "detector",
    ):
        assert default.configuration[key], f"the configuration does not name {key}"


@pytest.mark.trace("REQ-WP-010")
def test_the_report_cannot_be_edited_after_the_fact(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-013. A run's result is what the run produced."""
    report = _run(falling_with_breakouts)

    with pytest.raises(ValidationError):
        report.candidates_opened = 999  # type: ignore[misc]


@pytest.mark.trace("REQ-WP-010")
def test_the_report_carries_no_economic_metric() -> None:
    """FR-012, SC-007, ADR-009.

    Over the field names rather than over one instance, so this fails when
    someone adds `win_rate` -- not only when a particular run populates it. The
    metric is computable; the point is that it would be quoted without the fees
    and slippage PRD section 41 rule 9 requires, and a caveat does not travel
    with a number.
    """
    names = set(BacktestReport.model_fields) | {
        name for name in dir(BacktestReport) if not name.startswith("_")
    }
    leaked = names & FORBIDDEN_ECONOMIC_FIELDS
    assert not leaked, (
        f"{sorted(leaked)} is an economic metric; ADR-009 says the report carries none "
        "until an outcome definition and a cost model exist. Revisit the ADR, not this test."
    )
