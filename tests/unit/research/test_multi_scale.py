"""EXP-016's multi-scale nesting rules (REQ-EXP-016)."""

from __future__ import annotations

import pytest

from channelflow.backtest import CostModel, Outcome, SignalOutcome
from channelflow.research.multi_scale import (
    COSTS_THE_TOTAL,
    IMPROVES_BOTH,
    IMPROVES_NEITHER,
    RULES,
    UNMEASURED,
    Candidate,
    HigherFrame,
    OutOfOrder,
    UnknownRule,
    aligned_with_higher_slope,
    available_frame,
    confirmed_at_multiple_scales,
    evaluate_nesting,
    inside_higher_zone,
)

SECOND = 1_000_000_000
BASE_STEP = 300 * SECOND
MID_STEP = 900 * SECOND
HIGH_STEP = 3600 * SECOND
COSTS = CostModel(fee_bps=1.0, slippage_bps=1.0)
RISK = 0.01
FLOOR = 0.01

#: Every mid frame carries the same zone, so the rule's decision depends on the
#: candidate's price and nothing else.
ZONE = (100.0, 110.0)
IN_ZONE, OUT_OF_ZONE = 105.0, 120.0


def outcome(as_of_ns: int, *, ret: float) -> SignalOutcome:
    won = ret > 0.0
    return SignalOutcome(
        horizon_end_ns=as_of_ns + HIGH_STEP,
        first_target_time_ns=as_of_ns + BASE_STEP if won else None,
        first_invalidation_time_ns=None if won else as_of_ns + BASE_STEP,
        mfe_pct=abs(ret),
        mae_pct=abs(ret) / 10.0,
        return_h=ret,
        outcome=Outcome.TARGET if won else Outcome.STOP,
    )


def mid_frames(n: int = 40) -> list[HigherFrame]:
    return [
        HigherFrame(closed_ns=(i + 1) * MID_STEP, zone_low=ZONE[0], zone_high=ZONE[1], slope=0.0)
        for i in range(n)
    ]


def high_frames(n: int = 12) -> list[HigherFrame]:
    """Always rising, so "long" is the aligned direction throughout."""
    return [
        HigherFrame(closed_ns=(i + 1) * HIGH_STEP, zone_low=0.0, zone_high=1e9, slope=1.0)
        for i in range(n)
    ]


def candidates(n: int = 60, *, zone_wins: bool = True) -> list[Candidate]:
    """Half inside the mid zone, half of those aligned with the high slope.

    Being inside the zone decides the outcome; being aligned adds a hair. That
    makes the zone rule genuinely valuable and the alignment rule a filter that
    reads better per trade and takes half the book away.
    """
    built = []
    for k in range(n):
        as_of_ns = HIGH_STEP + k * BASE_STEP
        inside = k % 2 == 0
        long = k % 4 in (0, 1)
        edge = 0.03 if inside == zone_wins else -0.02
        built.append(
            Candidate(
                as_of_ns=as_of_ns,
                price=IN_ZONE if inside else OUT_OF_ZONE,
                direction="long" if long else "short",
                outcome=outcome(as_of_ns, ret=edge + (0.001 if long else 0.0)),
            )
        )
    return built


def run(built: list[Candidate] | None = None, **kwargs: object):
    return evaluate_nesting(
        built if built is not None else candidates(),
        mid_frames=mid_frames(),
        high_frames=high_frames(),
        costs=COSTS,
        risk_per_trade=RISK,
        improvement_floor=FLOOR,
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.trace("REQ-EXP-016")
def test_the_three_rules_the_prd_names_are_evaluated() -> None:
    """5m candidate inside the 15m zone; 15m candidate aligned with the 1h
    slope; directional-change thresholds at multiple scales."""
    assert RULES == (
        "inside_higher_zone",
        "aligned_with_higher_slope",
        "confirmed_at_multiple_scales",
    )

    report = run()

    assert list(report.rules) == list(RULES)


@pytest.mark.trace("REQ-EXP-016")
def test_a_rule_outside_the_three_is_refused() -> None:
    with pytest.raises(UnknownRule, match="eyeballed_it"):
        run(rules=("eyeballed_it",))


@pytest.mark.trace("REQ-EXP-016")
def test_every_rule_reports_the_average_trade_and_the_total() -> None:
    """ "Measure incremental value, not visual appeal."

    A chart of the survivors shows the first number and cannot show the second,
    because the trades a filter removed are not on it.
    """
    report = run()

    for result in report.rules.values():
        assert result.expectancy_delta is not None
        assert result.total_r_delta is not None
        assert result.selectivity is not None
        assert result.kept.total_r is not None
        assert result.base.total_r is not None
    assert "not visual appeal" in report.note


@pytest.mark.trace("REQ-EXP-016")
def test_a_rule_that_earns_its_selectivity_is_named_as_such() -> None:
    """Being inside the zone decides the outcome in this fixture, so the rule
    keeps half the candidates and more than doubles the average trade -- which is
    what it takes for a filter to come out ahead in total as well."""
    report = run()

    zone = report.rules["inside_higher_zone"]
    assert zone.selectivity == pytest.approx(0.5)
    assert zone.reading == IMPROVES_BOTH
    assert zone.total_r_delta is not None and zone.total_r_delta > 0.0


@pytest.mark.trace("REQ-EXP-016")
def test_a_rule_that_looks_better_than_it_is_is_named_as_such() -> None:
    """The finding EXP-016's last sentence exists to produce.

    Alignment with the higher slope lifts the average trade here -- and takes
    half the book away to do it, so the total falls. A chart of the aligned
    candidates shows only the lift.
    """
    report = run()

    aligned = report.rules["aligned_with_higher_slope"]
    assert aligned.expectancy_delta is not None and aligned.expectancy_delta >= FLOOR
    assert aligned.total_r_delta is not None and aligned.total_r_delta < 0.0
    assert aligned.reading == COSTS_THE_TOTAL
    assert "aligned_with_higher_slope" in report.better_looking_than_they_are


@pytest.mark.trace("REQ-EXP-016")
def test_a_rule_that_helps_neither_way_is_named_as_such() -> None:
    """The control: the same rule against a fixture where being inside the zone
    is what loses money."""
    report = run(candidates(zone_wins=False))

    assert report.rules["inside_higher_zone"].reading == IMPROVES_NEITHER


@pytest.mark.trace("REQ-EXP-016")
def test_the_rejected_candidates_are_reported_too() -> None:
    """EXP-016 names "aligned/conflicted" as a pair. The conflicted set is an
    arm of the experiment, not a discard."""
    report = run()

    aligned = report.rules["aligned_with_higher_slope"]
    assert aligned.rejected.trades > 0
    assert aligned.rejected.trades + aligned.kept.trades == aligned.base.trades


@pytest.mark.trace("REQ-EXP-016")
def test_only_a_closed_higher_frame_is_visible() -> None:
    """Principle I, at the easiest place in this experiment to lose it.

    A candidate sits *inside* a higher-timeframe bar that has not closed, and
    that bar's zone is partly made of what happened after the candidate. Reading
    it improves every number in the module.

    Here the frame containing the candidate would accept it and the last closed
    one does not, so the two answers differ.
    """
    as_of_ns = MID_STEP + 100 * SECOND
    frames = [
        # Closed before the candidate: its zone excludes the price.
        HigherFrame(closed_ns=MID_STEP, zone_low=0.0, zone_high=50.0, slope=1.0),
        # Contains the candidate and closes after it: its zone would accept.
        HigherFrame(closed_ns=2 * MID_STEP, zone_low=0.0, zone_high=1e9, slope=1.0),
    ]

    visible = available_frame(frames, as_of_ns)

    assert visible is not None and visible.closed_ns == MID_STEP

    report = evaluate_nesting(
        [
            Candidate(
                as_of_ns=as_of_ns,
                price=IN_ZONE,
                direction="long",
                outcome=outcome(as_of_ns, ret=0.03),
            )
        ],
        mid_frames=frames,
        high_frames=[HigherFrame(closed_ns=1, zone_low=0.0, zone_high=1e9, slope=1.0)],
        costs=COSTS,
        risk_per_trade=RISK,
        improvement_floor=FLOOR,
    )

    assert report.rules["inside_higher_zone"].kept.trades == 0


@pytest.mark.trace("REQ-EXP-016")
def test_frames_out_of_closing_order_are_refused() -> None:
    """Out of order, "the last frame that had closed" is whichever one happened
    to be last in the list."""
    shuffled = [
        HigherFrame(closed_ns=2 * MID_STEP, zone_low=0.0, zone_high=1e9, slope=1.0),
        HigherFrame(closed_ns=MID_STEP, zone_low=0.0, zone_high=50.0, slope=1.0),
    ]

    with pytest.raises(OutOfOrder):
        available_frame(shuffled, 3 * MID_STEP)


@pytest.mark.trace("REQ-EXP-016")
def test_a_candidate_without_context_is_excluded_from_every_arm() -> None:
    """Scoring it in the base and not in the filtered arm would make the warm-up
    look like the rule's contribution."""
    early = Candidate(
        as_of_ns=BASE_STEP,
        price=IN_ZONE,
        direction="long",
        outcome=outcome(BASE_STEP, ret=0.03),
    )
    built = [early, *candidates()]

    report = run(built)

    assert report.candidates == len(built)
    assert report.without_context == 1
    assert report.rules["inside_higher_zone"].base.trades == len(built) - 1


@pytest.mark.trace("REQ-EXP-016")
def test_a_rule_that_keeps_nothing_has_no_expectancy() -> None:
    """Zero there would let a rule that kept nothing rank alongside one that
    broke even, and only one of those was measured."""
    outside = [
        Candidate(
            as_of_ns=HIGH_STEP + k * BASE_STEP,
            price=OUT_OF_ZONE,
            direction="long",
            outcome=outcome(HIGH_STEP + k * BASE_STEP, ret=0.03),
        )
        for k in range(10)
    ]

    report = run(outside)

    zone = report.rules["inside_higher_zone"]
    assert zone.kept.trades == 0
    assert zone.kept.expectancy_r is None
    assert zone.kept.total_r is None
    assert zone.expectancy_delta is None
    assert zone.reading == UNMEASURED


@pytest.mark.trace("REQ-EXP-016")
def test_the_improvement_floor_is_required_and_positive() -> None:
    """It decides what counts as an improvement in R, and both readings move
    with it. PRD section 13A.27's warning applies."""
    with pytest.raises(TypeError):
        evaluate_nesting(  # type: ignore[call-arg]
            candidates(),
            mid_frames=mid_frames(),
            high_frames=high_frames(),
            costs=COSTS,
            risk_per_trade=RISK,
        )

    with pytest.raises(ValueError, match="improvement_floor"):
        evaluate_nesting(
            candidates(),
            mid_frames=mid_frames(),
            high_frames=high_frames(),
            costs=COSTS,
            risk_per_trade=RISK,
            improvement_floor=0.0,
        )


@pytest.mark.trace("REQ-EXP-016")
def test_a_direction_that_is_neither_long_nor_short_is_refused() -> None:
    with pytest.raises(ValueError, match="sideways"):
        Candidate(
            as_of_ns=HIGH_STEP,
            price=IN_ZONE,
            direction="sideways",
            outcome=outcome(HIGH_STEP, ret=0.01),
        )


@pytest.mark.trace("REQ-EXP-016")
def test_two_runs_produce_equal_reports() -> None:
    built = candidates()

    assert run(built).rules == run(built).rules


@pytest.mark.trace("REQ-EXP-016")
def test_multiple_scales_means_both_of_them() -> None:
    """ "Directional-change thresholds at multiple scales" is a conjunction.

    Either scale on its own is one of the first two rules already. A third rule
    that fired when *either* agreed would be a looser version of them wearing
    the name of a stricter one.
    """
    mid = HigherFrame(closed_ns=1, zone_low=ZONE[0], zone_high=ZONE[1], slope=0.0)
    rising = HigherFrame(closed_ns=1, zone_low=0.0, zone_high=1e9, slope=1.0)

    inside_but_conflicted = Candidate(
        as_of_ns=HIGH_STEP, price=IN_ZONE, direction="short", outcome=outcome(HIGH_STEP, ret=0.01)
    )
    aligned_but_outside = Candidate(
        as_of_ns=HIGH_STEP,
        price=OUT_OF_ZONE,
        direction="long",
        outcome=outcome(HIGH_STEP, ret=0.01),
    )

    assert inside_higher_zone(inside_but_conflicted, mid, rising)
    assert not aligned_with_higher_slope(inside_but_conflicted, mid, rising)
    assert not confirmed_at_multiple_scales(inside_but_conflicted, mid, rising)

    assert aligned_with_higher_slope(aligned_but_outside, mid, rising)
    assert not inside_higher_zone(aligned_but_outside, mid, rising)
    assert not confirmed_at_multiple_scales(aligned_but_outside, mid, rising)


@pytest.mark.trace("REQ-EXP-016")
def test_the_zone_includes_its_own_edges() -> None:
    """A candidate at the edge of the zone is in the zone.

    The edge is where these candidates actually are -- a 5-minute extremum is
    interesting precisely because it printed at the boundary of the higher
    timeframe's range -- so an exclusive bound drops the population the rule
    exists to select.
    """
    mid = HigherFrame(closed_ns=1, zone_low=ZONE[0], zone_high=ZONE[1], slope=0.0)
    rising = HigherFrame(closed_ns=1, zone_low=0.0, zone_high=1e9, slope=1.0)

    for price in ZONE:
        at_the_edge = Candidate(
            as_of_ns=HIGH_STEP,
            price=price,
            direction="long",
            outcome=outcome(HIGH_STEP, ret=0.01),
        )
        assert inside_higher_zone(at_the_edge, mid, rising)


@pytest.mark.trace("REQ-EXP-016")
def test_the_improvement_floor_decides_what_counts_as_an_improvement() -> None:
    """Not the sign of the difference.

    The zone rule lifts the average trade by about three R on this fixture. At a
    floor above that, nothing counts -- and it is the floor doing that, not the
    data.
    """
    built = candidates()

    modest = run(built)
    demanding = evaluate_nesting(
        built,
        mid_frames=mid_frames(),
        high_frames=high_frames(),
        costs=COSTS,
        risk_per_trade=RISK,
        improvement_floor=50.0,
    )

    assert modest.rules["inside_higher_zone"].reading == IMPROVES_BOTH
    assert demanding.rules["inside_higher_zone"].reading == IMPROVES_NEITHER
