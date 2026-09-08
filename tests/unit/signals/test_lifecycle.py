"""The candidate lifecycle (REQ-WP-007, PRD section 21.2)."""

from __future__ import annotations

import pytest

from channelflow.signals import CandidateState, IllegalTransition, SignalMachine
from tests.unit.signals.conftest import bar_at, channel


def _run(positions: list[float], **kwargs) -> list[CandidateState]:
    machine = SignalMachine(**kwargs)
    states = []
    for i, pos in enumerate(positions):
        candidate = machine.on_bar(bar_at(pos, index=i), channel(index=i))
        states.append(candidate.state if candidate else CandidateState.NONE)
    return states


@pytest.mark.trace("REQ-WP-007")
def test_approach_touch_reject_confirm_is_the_path() -> None:
    """SC-001. A zone touch is only a candidate -- PRD section 21.2 -- and each
    step has to be earned separately."""
    states = _run([0.90, 1.00, 0.70, 0.65])

    assert states == [
        CandidateState.APPROACH,
        CandidateState.TOUCH,
        CandidateState.REJECTION_PENDING,
        CandidateState.CONFIRMED,
    ]


@pytest.mark.trace("REQ-WP-007")
def test_price_outside_every_zone_opens_nothing() -> None:
    # Between the zones: lower ends at 0.12, middle runs 0.44-0.56, upper starts
    # at 0.88. 0.30 and 0.70 sit in the gaps on purpose.
    assert _run([0.30, 0.70, 0.25]) == [CandidateState.NONE] * 3


@pytest.mark.trace("REQ-WP-007")
def test_the_same_bars_twice_give_identical_paths_and_records() -> None:
    """SC-002. PRD section 0.13 wants results reproducible from a dataset and a
    commit hash; a machine whose path drifts cannot deliver that."""
    positions = [0.90, 1.00, 0.70, 0.65, 0.60]

    def run_full():
        machine = SignalMachine()
        for i, pos in enumerate(positions):
            machine.on_bar(bar_at(pos, index=i), channel(index=i))
        return machine.candidate

    first, second = run_full(), run_full()
    assert first == second
    assert [t.reason for t in first.history] == [t.reason for t in second.history]


@pytest.mark.trace("REQ-WP-007")
def test_no_transition_skips_a_step() -> None:
    """SC-007. Checked over the recorded history rather than asserted about the
    code: every edge taken must be one the lifecycle lists."""
    from channelflow.signals.models import ALLOWED

    machine = SignalMachine()
    for i, pos in enumerate([0.90, 1.00, 0.70, 0.65]):
        machine.on_bar(bar_at(pos, index=i), channel(index=i))

    for transition in machine.candidate.history:
        assert transition.to_state in ALLOWED[transition.from_state], (
            f"{transition.from_state.value} -> {transition.to_state.value} is not a legal edge"
        )


@pytest.mark.trace("REQ-WP-007")
def test_an_illegal_move_is_refused_rather_than_performed() -> None:
    """The guard itself. A machine that could jump from touch to confirmed would
    emit signals that never rejected, indistinguishable downstream from real."""
    machine = SignalMachine()
    machine.on_bar(bar_at(0.90, index=0), channel(index=0))

    with pytest.raises(IllegalTransition, match="not a legal move"):
        machine._advance(bar_at(0.90, index=1), CandidateState.CONFIRMED, "skipping")


@pytest.mark.trace("REQ-WP-007")
def test_a_long_setup_opens_at_the_lower_boundary() -> None:
    """FR-002, family B. Symmetric to A, through the same table."""
    machine = SignalMachine()
    for i, pos in enumerate([0.10, 0.00]):
        machine.on_bar(bar_at(pos, index=i), channel(slope=0.5, quality=0.8, index=i))

    assert machine.candidate.direction == "long"
    assert machine.candidate.boundary == "lower"
    assert machine.candidate.state is CandidateState.TOUCH
