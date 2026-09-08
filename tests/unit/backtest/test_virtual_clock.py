"""Every timestamp comes from the data (REQ-WP-010)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from channelflow.backtest import BacktestRunner
from channelflow.bars import Bar
from channelflow.channels import RollingOLSChannel
from channelflow.signals import SignalMachine


def _runner() -> BacktestRunner:
    return BacktestRunner(channel=RollingOLSChannel(lookback=60), machine=SignalMachine())


@pytest.mark.trace("REQ-WP-010")
def test_two_runs_over_the_same_bars_are_identical(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-006, SC-002.

    Both runs go through one runner instance deliberately. The signal machine
    carries the live candidate, so a runner that drove the caller's machine
    directly would start its second run mid-lifecycle and quietly report
    something else.
    """
    runner = _runner()

    assert runner.run(falling_with_breakouts) == runner.run(falling_with_breakouts)


@pytest.mark.trace("REQ-WP-010")
def test_a_run_does_not_disturb_the_machine_it_was_given(
    falling_with_breakouts: list[Bar],
) -> None:
    """The same property from the caller's side."""
    machine = SignalMachine()
    BacktestRunner(channel=RollingOLSChannel(lookback=60), machine=machine).run(
        falling_with_breakouts
    )

    assert machine.candidate is None, "the run mutated the machine handed to it"


@pytest.mark.trace("REQ-WP-010")
def test_bars_are_replayed_in_event_time_order(falling_with_breakouts: list[Bar]) -> None:
    """FR-001. US1 acceptance scenario 4."""
    shuffled = list(falling_with_breakouts)
    random.Random(20260908).shuffle(shuffled)

    assert _runner().run(shuffled) == _runner().run(falling_with_breakouts)


@pytest.mark.trace("REQ-WP-010")
def test_unfinalized_bars_are_not_replayed(falling_with_breakouts: list[Bar]) -> None:
    """A bar still forming can still change. Acting on it is acting on a guess."""
    provisional = falling_with_breakouts[-1].model_copy(update={"is_final": False})
    with_provisional = [*falling_with_breakouts[:-1], provisional]

    report = _runner().run(with_provisional)

    assert report.bars_replayed == len(falling_with_breakouts) - 1
    assert report.last_bar_close_ns == falling_with_breakouts[-2].close_time_ns


@pytest.mark.trace("REQ-WP-010")
def test_the_backtest_cannot_consult_a_clock() -> None:
    """FR-003, SC-001 for US3. Asserted over the source, as the bar builder is.

    A backtest that read the wall clock would give a different answer tomorrow,
    and the difference would look like a finding.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "backtest"
    modules = list(package.glob("*.py"))
    assert modules, "the backtest package has no modules; this test would pass vacuously"
    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"


class _RecordingChannel(RollingOLSChannel):
    """A channel that remembers what it was shown.

    `RollingOLSChannel.fit` filters by `as_of` itself (REQ-WP-006), and the
    runner also slices the history. Either guard alone prevents lookahead, so
    breaking one of them changes no result and no test notices. This watches
    what the runner hands over, which is the thing the redundancy hides.
    """

    calls: list[tuple[int, int]] = []  # noqa: RUF012 -- shared by design, cleared per test

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> object:  # type: ignore[override]
        latest = max((b.close_time_ns for b in bars), default=0)
        type(self).calls.append((latest, as_of_ns))
        return super().fit(bars, as_of_ns=as_of_ns)


@pytest.mark.trace("REQ-WP-010")
def test_the_runner_never_shows_the_channel_a_future_bar(
    falling_with_breakouts: list[Bar],
) -> None:
    """FR-004. PRD section 13.1: `source_max_event_time <= as_of`.

    A backtest that fits on bars it could not have had looks superb, which is
    exactly why Constitution Principle I holds "even when violating it would
    improve a backtest".
    """
    channel = _RecordingChannel(lookback=60)
    _RecordingChannel.calls = []

    report = BacktestRunner(channel=channel, machine=SignalMachine()).run(falling_with_breakouts)
    calls = _RecordingChannel.calls

    assert len(calls) == report.bars_replayed, "not every bar reached the channel"
    closes = [bar.close_time_ns for bar in falling_with_breakouts]
    for (latest_shown, as_of), expected in zip(calls, closes, strict=True):
        assert as_of == expected, "the fit was asked about a bar other than the current one"
        assert latest_shown <= as_of, "the runner showed the channel a bar from the future"
