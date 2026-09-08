"""Replay produces exactly what live would have (REQ-WP-010).

PRD section 25.2: the same production code should run in replay, and a separate
backtest implementation of strategy logic must be avoided. Section 35.5 asks for
replay parity. Constitution Principle VII says live and replay are the same code.

Asserting that by reading the source would prove only that nobody has drifted
yet. This drives the live engine directly and the backtest over the same bars,
and demands the same answer -- every transition, in order, with its reason.

The live driver here collects transitions by their own `bar_close_time_ns`
rather than by tracking candidate identity, which is how the runner does it.
Two derivations, one answer: a bookkeeping bug in either shows up as a
divergence rather than cancelling out.
"""

from __future__ import annotations

import pytest

from channelflow.backtest import BacktestRunner
from channelflow.bars import Bar
from channelflow.channels import ChannelFitError, RollingOLSChannel
from channelflow.signals import CandidateState, SignalMachine, Transition

LOOKBACK = 60


def _drive_live(bars: list[Bar]) -> list[Transition]:
    """The live path: fit a channel per bar, feed the machine, keep what moved."""
    model = RollingOLSChannel(lookback=LOOKBACK)
    machine = SignalMachine()
    seen: list[Transition] = []
    for i, bar in enumerate(bars):
        try:
            channel = model.fit(bars[: i + 1], as_of_ns=bar.close_time_ns)
        except ChannelFitError:
            channel = None
        candidate = machine.on_bar(bar, channel)
        if candidate is None:
            continue
        seen.extend(t for t in candidate.history if t.bar_close_time_ns == bar.close_time_ns)
    return seen


@pytest.mark.trace("REQ-WP-010")
def test_replay_matches_the_live_engine_transition_for_transition(
    falling_with_breakouts: list[Bar],
) -> None:
    """SC-001. A divergence here is the two implementations having drifted."""
    live = _drive_live(falling_with_breakouts)
    replayed = BacktestRunner(
        channel=RollingOLSChannel(lookback=LOOKBACK), machine=SignalMachine()
    ).run(falling_with_breakouts)

    assert live, "the fixture must actually produce transitions, or this proves nothing"
    assert list(replayed.transitions) == live, "replay and live disagreed about the candidate path"


@pytest.mark.trace("REQ-WP-010")
def test_parity_covers_a_full_lifecycle_not_just_openings(
    falling_with_breakouts: list[Bar],
) -> None:
    """Guard on the guard.

    A fixture that only ever opens candidates would let a runner that drops
    every later transition pass the parity test. This pins what the comparison
    above is actually comparing: more than one candidate, and states past the
    first step.
    """
    report = BacktestRunner(
        channel=RollingOLSChannel(lookback=LOOKBACK), machine=SignalMachine()
    ).run(falling_with_breakouts)

    assert report.candidates_opened > 1, "the fixture generated no repeated setups"
    reached = set(report.states_reached)
    assert reached - {CandidateState.APPROACH}, "no candidate ever moved past its opening"
