"""Expiry, no revival, and detector plugability (REQ-WP-007)."""

from __future__ import annotations

import pytest

from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.signals import CandidateState, SignalMachine
from tests.unit.signals.conftest import bar_at, channel


@pytest.mark.trace("REQ-WP-007")
def test_a_candidate_expires_after_the_configured_bars() -> None:
    """SC-005, PRD section 21.6. A candidate confirming twenty bars after its
    touch is describing a different event than the one it opened for."""
    machine = SignalMachine(expiry_bars=3)
    machine.on_bar(bar_at(0.95, index=0), channel(index=0))
    for i in range(1, 5):
        machine.on_bar(bar_at(0.95, index=i), channel(index=i))

    assert machine.candidate.state is CandidateState.EXPIRED
    assert "no confirmation in 3 bars" in machine.candidate.history[-1].reason


@pytest.mark.trace("REQ-WP-007")
def test_an_expired_candidate_does_not_revive() -> None:
    """SC-005, FR-012. Reviving would let a stale candidate confirm on price
    action it never approached."""
    machine = SignalMachine(expiry_bars=2)
    machine.on_bar(bar_at(0.95, index=0), channel(index=0))
    for i in range(1, 4):
        machine.on_bar(bar_at(0.95, index=i), channel(index=i))
    expired = machine.candidate
    assert expired.state is CandidateState.EXPIRED

    # Price action that would have confirmed, arriving too late.
    machine.on_bar(bar_at(0.60, index=9), channel(index=9))
    assert machine.candidate.state is not CandidateState.CONFIRMED


@pytest.mark.trace("REQ-WP-007")
def test_a_confirmed_candidate_does_not_expire() -> None:
    """FR-011 applies to unconfirmed candidates only."""
    machine = SignalMachine(expiry_bars=3)
    for i, pos in enumerate([0.95, 1.00, 0.70, 0.65]):
        machine.on_bar(bar_at(pos, index=i), channel(index=i))
    assert machine.candidate.state is CandidateState.CONFIRMED

    for i in range(4, 10):
        machine.on_bar(bar_at(0.60, index=i), channel(index=i))
    assert machine.candidate.state is not CandidateState.EXPIRED


@pytest.mark.trace("REQ-WP-007")
def test_a_second_detector_registers_without_touching_the_machine() -> None:
    """SC-008, FR-013. PRD section 21.3 lists four detectors; three need
    confirmation features that do not exist. This proves they are additions."""

    class NeverRejects:
        name = "never"

        def rejected(
            self, bar: Bar, channel_: ChannelSnapshot, *, boundary: str, direction: str
        ) -> bool:
            return False

    machine = SignalMachine(detector=NeverRejects(), expiry_bars=50)
    for i, pos in enumerate([0.95, 1.00, 0.70, 0.65]):
        machine.on_bar(bar_at(pos, index=i), channel(index=i))

    assert machine.candidate.state is CandidateState.TOUCH, (
        "with a detector that never rejects, the candidate cannot get past touch"
    )
