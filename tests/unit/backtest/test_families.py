"""One setup family at a time (REQ-US-005, PRD sections 31 and 25.2)."""

from __future__ import annotations

import pytest

from channelflow.backtest import BacktestRunner
from channelflow.backtest.families import (
    MIDDLE_CONTINUATION_SHORT,
    UPPER_REJECTION_SHORT,
    SetupFamily,
)
from channelflow.bars import Bar


@pytest.mark.trace("REQ-US-005")
def test_a_family_run_opens_only_its_own_candidates(falling_with_breakouts: list[Bar]) -> None:
    """SC-001, FR-002.

    REQ-US-005 wants `upper_rejection_short` backtested "окремо" -- separately.
    A run that also opened middle-zone setups would be reporting a mixture under
    one family's name.
    """
    report = BacktestRunner(family=UPPER_REJECTION_SHORT).run(falling_with_breakouts)

    assert report.candidates_opened > 0, "the fixture must open this family, or nothing is tested"
    assert set(report.by_boundary) == {"upper"}
    assert set(report.by_direction) == {"short"}


@pytest.mark.trace("REQ-US-005")
def test_the_other_family_runs_on_the_same_bars_and_sees_its_own(
    falling_with_breakouts: list[Bar],
) -> None:
    """SC-001, FR-002."""
    report = BacktestRunner(family=MIDDLE_CONTINUATION_SHORT).run(falling_with_breakouts)

    assert report.candidates_opened > 0
    assert set(report.by_boundary) == {"middle"}


@pytest.mark.trace("REQ-US-005")
def test_neither_familys_count_depends_on_the_others_setups(
    falling_with_breakouts: list[Bar],
) -> None:
    """SC-002, FR-002, FR-009.

    The engine tracks one candidate at a time, so a middle-zone setup occupies
    the machine and the upper-zone setup two bars later never opens. Filtering a
    finished report would leave exactly that interference in the counts while
    looking clean -- which is why the restriction is on what may open.

    The unrestricted run is the control: it opens fewer of this family's
    candidates than the family's own run, because the other family took the
    machine.
    """
    # Same thresholds as the default machine, so the only difference between
    # the two runs is which setups may open. `UPPER_REJECTION_SHORT` also
    # raises the quality floor to PRD §31's 0.70, and comparing against it would
    # measure both changes at once.
    isolated = SetupFamily(
        name="upper_only",
        boundary="upper",
        direction="short",
        zone=(0.88, 1.00),
        min_quality=0.5,
    )

    family_only = BacktestRunner(family=isolated).run(falling_with_breakouts)
    mixed = BacktestRunner().run(falling_with_breakouts)

    assert mixed.by_boundary.get("middle", 0) > 0, (
        "the fixture must open the other family, or there is no interference to remove"
    )
    assert family_only.by_boundary.get("upper", 0) > mixed.by_boundary.get("upper", 0)


@pytest.mark.trace("REQ-US-005")
def test_the_report_names_the_family(falling_with_breakouts: list[Bar]) -> None:
    """SC-003, FR-004.

    Two reports that cannot be told apart are two reports whose difference
    cannot be attributed -- the reasoning the report's `configuration` field
    already follows.
    """
    named = BacktestRunner(family=UPPER_REJECTION_SHORT).run(falling_with_breakouts)
    unnamed = BacktestRunner().run(falling_with_breakouts)

    assert named.family == "upper_rejection_short"
    assert unnamed.family is None


@pytest.mark.trace("REQ-US-005")
def test_a_family_less_run_is_unchanged(falling_with_breakouts: list[Bar]) -> None:
    """SC-006, FR-005.

    Every existing caller passes no family. If the default changed behaviour,
    REQ-WP-010's parity test would be comparing a different engine.
    """
    first = BacktestRunner().run(falling_with_breakouts)
    second = BacktestRunner().run(falling_with_breakouts)

    assert first.candidates_opened == second.candidates_opened
    assert set(first.by_boundary) >= {"upper", "middle"}


@pytest.mark.trace("REQ-US-005")
def test_upper_rejection_short_carries_the_prds_own_numbers() -> None:
    """SC-004, FR-006.

    PRD §31's `signals: upper_rejection_short:` block: a 0.70 quality floor, a
    zone starting at 0.88, and an overshoot tolerance of 0.08.
    """
    assert UPPER_REJECTION_SHORT.min_quality == pytest.approx(0.70)
    assert UPPER_REJECTION_SHORT.zone == (0.88, 1.00)
    assert UPPER_REJECTION_SHORT.overshoot_tolerance == pytest.approx(0.08)


@pytest.mark.trace("REQ-US-005")
def test_the_two_families_differ_in_configuration_not_in_code() -> None:
    """SC-004, FR-001.

    Families that differed only by name would make "backtest them separately" a
    distinction without a difference.
    """
    assert UPPER_REJECTION_SHORT.boundary != MIDDLE_CONTINUATION_SHORT.boundary
    assert UPPER_REJECTION_SHORT.zone != MIDDLE_CONTINUATION_SHORT.zone


@pytest.mark.trace("REQ-US-005")
def test_the_familys_thresholds_are_in_its_report(falling_with_breakouts: list[Bar]) -> None:
    """SC-004, FR-007.

    A report whose configuration does not include what the family changed cannot
    explain why two family runs differ.
    """
    report = BacktestRunner(family=UPPER_REJECTION_SHORT).run(falling_with_breakouts)

    assert report.configuration["family"] == "upper_rejection_short"
    assert report.configuration["min_quality"] == "0.7"


@pytest.mark.trace("REQ-US-005")
@pytest.mark.parametrize("zone", [(0.9, 0.5), (-0.1, 0.5), (0.5, 1.5)])
def test_an_impossible_zone_is_refused(zone: tuple[float, float]) -> None:
    """SC-005, FR-008.

    An inverted zone matches nothing and reports zero candidates, which reads as
    "this family found no setups" rather than as "this family cannot open one".
    """
    with pytest.raises(ValueError, match="zone"):
        SetupFamily(
            name="broken",
            boundary="upper",
            direction="short",
            zone=zone,
        )


@pytest.mark.trace("REQ-US-005")
def test_the_family_adds_no_strategy_logic() -> None:
    """SC-007, FR-010.

    PRD §25.2 forbids a separate backtest implementation and Principle VII says
    live and replay are the same code. A family is configuration; a transition
    rule here would be a second engine with a nicer name.
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3] / "src" / "channelflow" / "backtest" / "families.py"
    ).read_text()

    for forbidden in ("CandidateState.", "Transition(", "def on_bar", "rejected("):
        assert forbidden not in source, f"families.py contains engine logic: {forbidden!r}"


@pytest.mark.trace("REQ-US-005")
def test_a_family_restricts_direction_as_well_as_zone(
    rising_with_breakouts: list[Bar],
) -> None:
    """SC-001, FR-001, FR-002.

    The middle zone opens both directions -- short in a falling channel, long in
    a rising one. A restriction that matched the boundary alone would let
    `middle_continuation_short` open longs in a climbing market, and every
    fixture with a falling channel would agree with it.
    """
    mixed = BacktestRunner().run(rising_with_breakouts)
    assert mixed.by_direction.get("long", 0) > 0, (
        "the fixture must open long setups, or the direction restriction is untested"
    )

    report = BacktestRunner(family=MIDDLE_CONTINUATION_SHORT).run(rising_with_breakouts)

    assert report.by_direction.get("long", 0) == 0


@pytest.mark.trace("REQ-US-005")
def test_the_familys_zone_is_what_the_machine_uses(falling_with_breakouts: list[Bar]) -> None:
    """SC-004, FR-001.

    `UPPER_REJECTION_SHORT`'s zone happens to equal the engine's own default, so
    a family whose zone was quietly dropped would behave identically and every
    test would agree. A narrower zone is the case that separates them: fewer
    bars reach it, so fewer candidates open.
    """
    narrow = SetupFamily(
        name="upper_narrow",
        boundary="upper",
        direction="short",
        zone=(0.97, 1.00),
        min_quality=0.5,
    )
    wide = SetupFamily(
        name="upper_wide",
        boundary="upper",
        direction="short",
        zone=(0.70, 1.00),
        min_quality=0.5,
    )

    fewer = BacktestRunner(family=narrow).run(falling_with_breakouts)
    more = BacktestRunner(family=wide).run(falling_with_breakouts)

    assert more.candidates_opened > fewer.candidates_opened
