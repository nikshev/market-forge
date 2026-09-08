"""PRD section 44A's safety filters (REQ-WP-020).

Section 44A.16 ends: "No individual feature is allowed to bypass the safety
filters." Each test below removes one and checks it is still enforced.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.stops import PositionPhase, ReasonCode, StopPolicy

from .conftest import anchor, at, long_position, short_position


def policy(**kwargs: object) -> StopPolicy:
    defaults: dict[str, object] = {
        "min_improvement_bps": Decimal(10),
        "cooldown_ns": 0,
        "noise_multiple": Decimal(0),
    }
    defaults.update(kwargs)
    return StopPolicy(**defaults)  # type: ignore[arg-type]


def propose(pos, anchors, *, minute=10, market="110", noise="0.5", **kwargs):
    return policy(**kwargs.pop("policy", {})).propose(
        pos,
        anchors=anchors,
        at_ns=at(minute),
        market_price=Decimal(market),
        noise_distance=Decimal(noise),
        phase=PositionPhase.STRUCTURE_TRAIL,
        **kwargs,
    )


@pytest.mark.trace("REQ-WP-020")
def test_a_long_stop_never_moves_down() -> None:
    """SC-001, FR-001, PRD section 44A.2:

    LONG:  new_stop >= current_effective_stop
    """
    position = long_position(current_strategy_stop=Decimal("103"))

    proposal = propose(position, [anchor("98", known_at=1)])

    assert proposal.price == Decimal("103")
    assert ReasonCode.HELD_WOULD_WIDEN in proposal.reasons
    assert not proposal.moved


@pytest.mark.trace("REQ-WP-020")
def test_a_short_stop_never_moves_up() -> None:
    """SC-001, FR-001. The symmetric half -- a policy handling one side would
    pass every test above."""
    position = short_position(current_strategy_stop=Decimal("97"))

    proposal = propose(position, [anchor("102", known_at=1)], market="90")

    assert proposal.price == Decimal("97")
    assert not proposal.moved


@pytest.mark.trace("REQ-WP-020")
def test_a_tightening_anchor_moves_the_stop() -> None:
    """FR-004. The policy must actually do something, or the guards above are
    guarding nothing."""
    position = long_position()

    proposal = propose(position, [anchor("99", known_at=1)])

    assert proposal.price == Decimal("99")
    assert proposal.moved
    assert ReasonCode.STRUCTURAL_ANCHOR in proposal.reasons
    assert proposal.anchor is not None


@pytest.mark.trace("REQ-WP-020")
def test_an_anchor_from_the_future_is_never_used() -> None:
    """SC-003, FR-003, PRD section 44A.3:

        "no future-confirmed swing may be used before its known_at"

    This is REQ-WP-019's timestamp doing the job it was built for. Without the
    filter the stop moves on a swing nobody could have known about -- and the
    backtest that follows looks excellent.
    """
    position = long_position()

    proposal = propose(position, [anchor("99", known_at=50)], minute=10)

    assert proposal.price == Decimal("95")
    assert ReasonCode.HELD_NO_ANCHOR in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_the_same_anchor_is_used_once_it_is_knowable() -> None:
    """SC-003. The rule delays the anchor, it does not discard it."""
    position = long_position()

    proposal = propose(position, [anchor("99", known_at=5)], minute=10)

    assert proposal.price == Decimal("99")
    assert proposal.moved


@pytest.mark.trace("REQ-WP-020")
def test_every_proposal_carries_a_reason_including_holds() -> None:
    """SC-004, FR-004, ADR-032.

    Six different holds look identical downstream if the policy returns
    nothing. The reason code is what makes a careful policy distinguishable
    from a broken one.
    """
    position = long_position()

    moved = propose(position, [anchor("99", known_at=1)])
    held_future = propose(position, [anchor("99", known_at=99)])
    held_widen = propose(
        long_position(current_strategy_stop=Decimal("103")), [anchor("98", known_at=1)]
    )

    for proposal in (moved, held_future, held_widen):
        assert proposal.reasons, "a proposal with no reason explains nothing"
    assert held_future.reasons != held_widen.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_sub_threshold_improvement_holds() -> None:
    """SC-005, FR-005, PRD section 44A.17.

    An improvement too small to matter still costs an exchange call and implies
    a precision the market does not have.
    """
    position = long_position(current_strategy_stop=Decimal("99"))

    proposal = propose(
        position, [anchor("99.001", known_at=1)], policy={"min_improvement_bps": Decimal(50)}
    )

    assert proposal.price == Decimal("99")
    assert ReasonCode.HELD_BELOW_THRESHOLD in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_cooldown_holds_the_next_movement() -> None:
    """SC-005, FR-006, PRD section 44A.17's anti-churn."""
    position = long_position()
    engine = StopPolicy(
        min_improvement_bps=Decimal(1),
        cooldown_ns=10 * 60 * 1_000_000_000,
        noise_multiple=Decimal(0),
    )

    first = engine.propose(
        position,
        anchors=[anchor("99", known_at=1)],
        at_ns=at(10),
        market_price=Decimal("110"),
        noise_distance=Decimal("0.5"),
        phase=PositionPhase.STRUCTURE_TRAIL,
    )
    assert first.moved

    second = engine.propose(
        position.model_copy(update={"current_strategy_stop": first.price}),
        anchors=[anchor("101", known_at=1)],
        at_ns=at(12),
        market_price=Decimal("110"),
        noise_distance=Decimal("0.5"),
        phase=PositionPhase.STRUCTURE_TRAIL,
    )

    assert not second.moved
    assert ReasonCode.HELD_COOLDOWN in second.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_data_quality_freeze_holds_the_stop() -> None:
    """SC-005, FR-007, PRD section 44A.18.

    Falling back to a price-derived stop here would be the blind following
    section 44A.39 forbids.
    """
    position = long_position()

    proposal = propose(position, [anchor("99", known_at=1)], data_quality_ok=False)

    assert proposal.price == Decimal("95")
    assert ReasonCode.HELD_DATA_QUALITY in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_stop_beyond_the_market_is_refused() -> None:
    """FR-009. A long stop at or above the market is an immediate exit."""
    position = long_position()

    proposal = propose(position, [anchor("112", known_at=1)], market="110")

    assert proposal.price == Decimal("95")
    assert ReasonCode.REFUSED_BEYOND_MARKET in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_stop_inside_the_minimum_distance_holds() -> None:
    """FR-009, PRD section 44A.8. The concern section 44A.29 measures: a stop
    sitting in the noise gets taken out by it."""
    position = long_position()

    proposal = propose(position, [anchor("109.9", known_at=1)], market="110", noise="2")

    assert not proposal.moved
    assert ReasonCode.HELD_TOO_CLOSE in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_the_noise_buffer_pushes_the_stop_away_from_the_anchor() -> None:
    """FR-008, PRD section 44A.9."""
    position = long_position()

    proposal = propose(
        position,
        [anchor("99", known_at=1)],
        noise="1",
        policy={"noise_multiple": Decimal(2)},
    )

    assert proposal.price == Decimal("97"), "99 minus two times the noise distance"
    assert ReasonCode.NOISE_BUFFER_APPLIED in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_the_buffer_cannot_push_a_stop_past_the_monotonic_rule() -> None:
    """FR-001, and the ordering that makes it hold.

    The buffer is applied before the monotonic check, so a buffer wide enough
    to push the stop below the current one is refused rather than sneaking
    past. Checking monotonicity on the raw anchor would let it through.
    """
    position = long_position(current_strategy_stop=Decimal("98"))

    proposal = propose(
        position,
        [anchor("99", known_at=1)],
        noise="5",
        policy={"noise_multiple": Decimal(2)},
    )

    assert proposal.price == Decimal("98")
    assert ReasonCode.HELD_WOULD_WIDEN in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_position_whose_stop_is_on_the_wrong_side_cannot_exist() -> None:
    """The spec's third edge case: without an initial-risk contract there is
    nothing for any guard to be measured against."""
    with pytest.raises(ValueError, match="wrong side"):
        long_position(initial_stop_price=Decimal("105"))


@pytest.mark.trace("REQ-WP-020")
def test_a_buffer_may_not_loosen_the_stop_even_inside_the_initial_risk() -> None:
    """FR-001, and the case the other monotonic tests miss.

    The stop has already been tightened to 98; the initial contract is 95. A
    noise buffer that pushes a proposal to 96 *widens* risk against the current
    stop while staying inside the original contract — so the initial-risk guard
    lets it through and only the monotonic check refuses it.

    Found by mutation: removing the post-buffer monotonic check left every
    other test passing, because in those cases the initial-risk guard happened
    to catch the same proposal. Two guards over one property hide each other's
    absence, and this is the case that separates them.
    """
    position = long_position(current_strategy_stop=Decimal("98"))

    proposal = propose(
        position,
        [anchor("99", known_at=1)],
        noise="1.5",
        policy={"noise_multiple": Decimal(2)},
    )

    assert proposal.price == Decimal("98"), "96 would be a looser stop than 98"
    assert ReasonCode.HELD_WOULD_WIDEN in proposal.reasons


@pytest.mark.trace("REQ-WP-020")
def test_a_proposal_cannot_be_built_without_a_reason() -> None:
    """FR-004, ADR-032, enforced by the type rather than by habit.

    Every proposal in the current code passes a reason, so a behavioural test
    cannot tell whether the guarantee exists. This one constructs the thing the
    guarantee forbids.
    """
    from pydantic import ValidationError

    from channelflow.stops import PositionPhase, StopProposal

    with pytest.raises(ValidationError):
        StopProposal(
            price=Decimal("99"),
            anchor=None,
            reasons=(),
            at_ns=at(10),
            phase=PositionPhase.STRUCTURE_TRAIL,
        )
