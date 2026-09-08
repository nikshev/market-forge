"""Preconditions and invalidation (REQ-WP-007, PRD sections 21.1 and 21.5)."""

from __future__ import annotations

import pytest

from channelflow.signals import CandidateState, SignalMachine
from tests.unit.signals.conftest import bar_at, channel


@pytest.mark.trace("REQ-WP-007")
def test_a_low_quality_channel_opens_nothing() -> None:
    """SC-003. PRD section 1.2 puts the edge in the conditions, not the touch.
    A machine that opens regardless is a boundary detector wearing a signal's
    name."""
    machine = SignalMachine(min_quality=0.5)
    assert machine.on_bar(bar_at(0.95, index=0), channel(slope=-0.5, quality=0.2)) is None


@pytest.mark.trace("REQ-WP-007")
def test_a_channel_whose_slope_opposes_the_direction_opens_nothing() -> None:
    """SC-004. A short at the upper boundary of a rising channel is a bet
    against the structure that defined the boundary."""
    machine = SignalMachine()
    # Upper zone, but the channel is rising: family A wants a bearish channel.
    assert machine.on_bar(bar_at(0.95, index=0), channel(slope=+0.5, quality=0.8)) is None


@pytest.mark.trace("REQ-WP-007")
def test_the_same_price_action_opens_under_a_supporting_channel() -> None:
    """The other half of the two above: the price action is not what differs."""
    machine = SignalMachine()
    candidate = machine.on_bar(bar_at(0.95, index=0), channel(slope=-0.5, quality=0.8))
    assert candidate is not None
    assert candidate.direction == "short"


@pytest.mark.trace("REQ-WP-007")
def test_quality_collapse_invalidates_with_a_recorded_reason() -> None:
    """FR-010, SC-006. PRD section 21.5 lists quality collapse as invalidating."""
    machine = SignalMachine(min_quality=0.5)
    machine.on_bar(bar_at(0.95, index=0), channel(slope=-0.5, quality=0.8, index=0))
    machine.on_bar(bar_at(0.95, index=1), channel(slope=-0.5, quality=0.1, index=1))

    assert machine.candidate.state is CandidateState.INVALIDATED
    assert "quality" in machine.candidate.history[-1].reason


@pytest.mark.trace("REQ-WP-007")
def test_a_close_beyond_the_outer_tolerance_invalidates() -> None:
    """FR-009, SC-006. PRD section 21.5's first example."""
    machine = SignalMachine(overshoot_tolerance=0.08)
    machine.on_bar(bar_at(0.95, index=0), channel(index=0))
    machine.on_bar(bar_at(1.30, index=1), channel(index=1))

    assert machine.candidate.state is CandidateState.INVALIDATED
    assert "outer tolerance" in machine.candidate.history[-1].reason


@pytest.mark.trace("REQ-WP-007")
def test_no_channel_means_nothing_opens_and_nothing_advances() -> None:
    """FR-015. A signal derived from an absent channel is derived from nothing."""
    machine = SignalMachine()
    assert machine.on_bar(bar_at(0.95, index=0), None) is None

    machine.on_bar(bar_at(0.95, index=1), channel(index=1))
    before = machine.candidate
    machine.on_bar(bar_at(1.00, index=2), None)
    assert machine.candidate == before, "an absent channel must not advance a candidate"
