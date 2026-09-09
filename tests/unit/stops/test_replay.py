"""PRD section 44A.28's counterfactual evaluation (REQ-WP-020, REQ-BIAS-009).

Section 41 rule 9: "Fees/slippage must be included in economic evaluation."
This is the first economic evaluation in the repository, so it is the first
place the rule can apply -- see ADR-031.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.stops import (
    ComparisonReport,
    CostModel,
    NaiveATRTrailing,
    NaiveFixedPercent,
    PricePoint,
    Replay,
    StopPolicy,
)

from .conftest import anchor, at, long_position, point, short_position


def free() -> CostModel:
    """Zero costs, for the tests that are about mechanics rather than money."""
    return CostModel(taker_fee_bps=Decimal(0), slippage_bps=Decimal(0))


@pytest.mark.trace("REQ-WP-020")
def test_a_path_that_never_hits_the_stop_reports_no_exit(
    rising_path: list[PricePoint],
) -> None:
    """FR-012. "No exit" is a result, and it must not be reported as an R of
    zero -- which would read as a scratch trade."""
    outcome = Replay(costs=free()).run_adaptive(
        long_position(), rising_path, StopPolicy(cooldown_ns=0)
    )

    assert not outcome.exited
    assert outcome.realized_r is None


@pytest.mark.trace("REQ-WP-020")
@pytest.mark.trace("REQ-BIAS-009")
def test_realized_r_is_net_of_fees_and_slippage() -> None:
    """SC-007, FR-013, FR-014, PRD section 41 rule 9 and section 44A.23.

    Entry 100, initial stop 95, so R0 = 5. The stop is hit at 95; slippage of
    100 bps makes the executable exit 94.05, and a 100 bps taker fee on that
    is 0.9405.

        gross    = 94.05 - 100      = -5.95
        net      = -5.95 - 0.9405   = -6.8905
        R        = -6.8905 / 5      = -1.3781

    A gross figure would have said -1.19, which is the difference between a
    policy that looks acceptable and one that does not.
    """
    costs = CostModel(taker_fee_bps=Decimal(100), slippage_bps=Decimal(100))
    path = [point(0, "99"), point(1, "94")]

    outcome = Replay(costs=costs).run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))

    assert outcome.exited
    assert outcome.requested_stop_price == Decimal("95")
    assert outcome.realized_exit_price == Decimal("94.05")
    assert outcome.realized_r == pytest.approx(-1.3781, abs=1e-4)


@pytest.mark.trace("REQ-BIAS-009")
def test_slippage_is_always_adverse() -> None:
    """ADR-031. Slippage that sometimes favoured the position would be a
    rounding argument; on a stop it is always the wrong way."""
    costs = CostModel(slippage_bps=Decimal(100))

    long_exit, _ = costs.executable_exit(Decimal("100"), side="LONG")
    short_exit, _ = costs.executable_exit(Decimal("100"), side="SHORT")

    assert long_exit < Decimal("100"), "a long exits below its stop"
    assert short_exit > Decimal("100"), "a short exits above its stop"


@pytest.mark.trace("REQ-WP-020")
def test_the_exit_uses_the_executable_price_not_the_requested_stop() -> None:
    """FR-014, PRD section 44A.23: "A stop price is not a guaranteed fill
    price"."""
    costs = CostModel(taker_fee_bps=Decimal(0), slippage_bps=Decimal(50))
    path = [point(0, "99"), point(1, "94")]

    outcome = Replay(costs=costs).run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))

    assert outcome.realized_exit_price != outcome.requested_stop_price
    assert outcome.stop_slippage_bps == 50.0


@pytest.mark.trace("REQ-WP-020")
def test_the_premature_stop_metric_counts_targets_reached_after_the_stop() -> None:
    """SC-008, FR-015, PRD section 44A.29.

    "the user's concern that a trailing stop gets taken out by ordinary price
    noise" -- the position stops at 95 and the path then reaches its 115
    target, which is exactly the case the metric is for.
    """
    path = [point(0, "99"), point(1, "94"), point(2, "110"), point(3, "116")]

    outcome = Replay(costs=free()).run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))
    report = ComparisonReport(outcomes=(outcome,))

    assert outcome.reached_target_after_stop
    assert report.premature_stop_rate == 1.0


@pytest.mark.trace("REQ-WP-020")
def test_a_stop_that_was_right_does_not_count_as_premature() -> None:
    """SC-008. The metric must discriminate, or it is a count of exits."""
    path = [point(0, "99"), point(1, "94"), point(2, "90"), point(3, "85")]

    outcome = Replay(costs=free()).run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))

    assert outcome.exited
    assert not outcome.reached_target_after_stop
    assert ComparisonReport(outcomes=(outcome,)).premature_stop_rate == 0.0


@pytest.mark.trace("REQ-WP-020")
def test_the_premature_rate_is_never_reported_without_realized_r() -> None:
    """FR-015, PRD section 44A.29:

        "Do not optimize this metric alone: an infinitely wide stop would make
        it look good while destroying risk control. Always combine with
        realized expectancy and downside metrics."

    Made structural: the summary carries both or neither.
    """
    path = [point(0, "99"), point(1, "94"), point(2, "116")]
    outcome = Replay(costs=free()).run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))

    summary = ComparisonReport(outcomes=(outcome,)).summary

    assert "premature-stop rate" in summary
    assert "realized R" in summary


@pytest.mark.trace("REQ-WP-020")
def test_the_naive_baselines_are_comparable_on_one_path(
    rising_path: list[PricePoint],
) -> None:
    """FR-012, PRD section 44A.39: "naive trailing stop baseline is included in
    comparison"."""
    replay = Replay(costs=free())
    position = long_position()

    adaptive = replay.run_adaptive(position, rising_path, StopPolicy(cooldown_ns=0))
    fixed = replay.run_naive(position, rising_path, NaiveFixedPercent())
    atr = replay.run_naive(position, rising_path, NaiveATRTrailing())

    report = ComparisonReport(outcomes=(adaptive, fixed, atr))

    assert {o.policy for o in report.outcomes} == {
        "adaptive",
        "naive_fixed_percent",
        "naive_atr_trailing",
    }


@pytest.mark.trace("REQ-WP-020")
def test_the_naive_baseline_moves_more_often_than_the_structural_one(
    rising_path: list[PricePoint],
) -> None:
    """The comparison's actual content.

    A fixed-percent stop follows every tick up; a structural one waits for a
    confirmed swing. That difference is what the extra machinery buys, and
    without costs the naive policy's extra activity would be free.
    """
    replay = Replay(costs=free())
    position = long_position()

    adaptive = replay.run_adaptive(position, rising_path, StopPolicy(cooldown_ns=0))
    fixed = replay.run_naive(position, rising_path, NaiveFixedPercent())

    assert fixed.stop_updates > adaptive.stop_updates


@pytest.mark.trace("REQ-WP-020")
def test_a_naive_baseline_still_may_not_widen(rising_path: list[PricePoint]) -> None:
    """FR-001 applies to the baselines too.

    A baseline allowed to widen would not be a stop policy at all, and the
    comparison would be against something else entirely.
    """
    falling = [point(i, str(110 - i)) for i in range(8)]
    replay = Replay(costs=free())

    outcome = replay.run_naive(
        long_position(current_strategy_stop=Decimal("104")), falling, NaiveFixedPercent()
    )

    assert outcome.exited, "the falling path must reach the stop"
    assert outcome.requested_stop_price >= Decimal("104")


@pytest.mark.trace("REQ-WP-020")
def test_a_replay_is_deterministic(rising_path: list[PricePoint]) -> None:
    """SC-009, FR-016, Principle XI."""
    replay = Replay(costs=free())
    position = long_position()

    first = replay.run_adaptive(position, rising_path, StopPolicy(cooldown_ns=0))
    second = replay.run_adaptive(position, rising_path, StopPolicy(cooldown_ns=0))

    assert first == second


@pytest.mark.trace("REQ-WP-020")
def test_the_replay_counts_why_the_policy_held(rising_path: list[PricePoint]) -> None:
    """ADR-032's payoff.

    "This policy held 400 times, 380 of them for cooldown" is a finding about
    the configuration. "The policy held 400 times" is not.
    """
    outcome = Replay(costs=free()).run_adaptive(
        long_position(), rising_path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.reason_counts
    # At least one reason per decision -- a moved proposal can carry two, since
    # the noise buffer records itself alongside the anchor.
    assert sum(outcome.reason_counts.values()) >= len(rising_path)
    assert all(count > 0 for count in outcome.reason_counts.values())


@pytest.mark.trace("REQ-WP-020")
def test_a_short_position_replays_symmetrically() -> None:
    """FR-001, FR-013 on the other side."""
    path = [point(0, "101"), point(1, "106")]

    outcome = Replay(costs=free()).run_adaptive(short_position(), path, StopPolicy(cooldown_ns=0))

    assert outcome.exited
    assert outcome.realized_r == pytest.approx(-1.0), "stopped at the initial stop, so -1R"


@pytest.mark.trace("REQ-WP-020")
def test_the_stops_package_cannot_consult_a_clock() -> None:
    """SC-010, FR-017.

    The pattern is `time.monotonic`, not the bare word. Every other package
    checks for `monotonic` alone and that is fine there -- here the domain rule
    is *called* monotonic tightening (PRD section 44A.2), so the bare word
    appears a dozen times in legitimate prose.

    A guard that fires on correct code gets weakened by whoever hits it next,
    which is worse than a slightly narrower pattern.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "stops"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "time.monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"


@pytest.mark.trace("REQ-WP-020")
def test_no_anchor_kind_derives_a_stop_from_price_alone() -> None:
    """SC-010, FR-018, PRD section 44A.39: "no blind price-following path
    exists in default policy".

    Enforced by the enumeration having no such member: a policy cannot build an
    anchor it has no kind for.
    """
    from channelflow.stops import AnchorKind

    assert {k.value for k in AnchorKind} == {
        "confirmed_swing",
        "channel_boundary",
        "volume_node",
        "initial_stop",
    }


@pytest.mark.trace("REQ-WP-020")
def test_the_data_quality_freeze_fires_in_a_replay(rising_path: list[PricePoint]) -> None:
    """Section 44A.18's freeze, in the one place it is supposed to be observable.

    `PricePoint` has carried `data_quality_ok` since the replay was written and
    the replay never passed it to the policy, so the freeze could not fire on
    any replayed path -- and a counterfactual evaluation that cannot show the
    freeze is not evaluating the policy that runs live.
    """
    frozen = [
        PricePoint(
            at_ns=p.at_ns,
            price=p.price,
            noise_distance=p.noise_distance,
            anchors=p.anchors,
            data_quality_ok=False,
        )
        for p in rising_path
    ]

    outcome = Replay(costs=free()).run_adaptive(long_position(), frozen, StopPolicy(cooldown_ns=0))

    assert outcome.stop_updates == 0
    assert outcome.reason_counts.get("HELD_DATA_QUALITY") == len(frozen)


@pytest.mark.trace("REQ-WP-020")
def test_the_replay_records_the_excursion_the_position_saw(
    rising_path: list[PricePoint],
) -> None:
    """Section 25.5 wants MFE and MAE, and the replay is the only place that
    holds the path and the position side together.

    The path runs 101 to 112 from an entry of 100 with R0 = 5, so the best the
    position saw was +12/5 and the worst +1/5. Both positive here: it never
    traded below the entry, and reporting the adverse excursion as zero would
    say it did.
    """
    outcome = Replay(costs=free()).run_adaptive(
        long_position(), rising_path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.mfe_r == pytest.approx(12 / 5)
    assert outcome.mae_r == pytest.approx(1 / 5)
    assert outcome.points_observed == len(rising_path)


@pytest.mark.trace("REQ-WP-020")
def test_a_short_position_records_the_excursion_the_other_way_round() -> None:
    """The control for the sign convention. A path that falls is favourable to a
    short, and an excursion computed with the long convention would report this
    position's best moment as its worst."""
    falling = [point(i, str(99 - i)) for i in range(6)]

    outcome = Replay(costs=free()).run_adaptive(
        short_position(), falling, StopPolicy(cooldown_ns=0)
    )

    # Entry 100, R0 = 5, path 99 down to 94: the best the short saw was +6/5 and
    # the worst +1/5. With the long convention the two would swap sign, and the
    # position's best moment would be reported as its worst.
    assert outcome.mfe_r == pytest.approx(6 / 5)
    assert outcome.mae_r == pytest.approx(1 / 5)


@pytest.mark.trace("REQ-WP-020")
def test_a_position_that_never_stopped_has_no_holding_time(
    rising_path: list[PricePoint],
) -> None:
    """Reporting the last observed instant as one would make an unfinished path
    look like a completed trade."""
    outcome = Replay(costs=free()).run_adaptive(
        long_position(), rising_path, StopPolicy(cooldown_ns=0)
    )

    assert not outcome.exited
    assert outcome.exit_at_ns is None
    assert outcome.holding_ns is None


@pytest.mark.trace("REQ-WP-020")
def test_a_stopped_position_reports_when_it_ended() -> None:
    """And the stop distances it passed through on the way.

    Section 44A's median and 95th-percentile stop distance are quantiles of this
    list, and a quantile of a summary is not a quantile.
    """
    low = anchor("99", known_at=0)
    path = [point(i, str(101 + i), anchors=(low,)) for i in range(4)] + [point(4, "94")]

    outcome = Replay(costs=free()).run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))

    assert outcome.exited
    assert outcome.exit_at_ns == at(4)
    assert outcome.holding_ns == at(4) - at(0)
    assert len(outcome.stop_distances_r) == outcome.points_observed == 5
    assert all(distance >= 0.0 for distance in outcome.stop_distances_r)
