"""EXP-017's stop-management comparison (REQ-EXP-017)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from channelflow.research.stop_policies import (
    ABLATIONS,
    EDGE,
    ENGINE,
    METRICS,
    NO_EDGE,
    POLICIES,
    Capabilities,
    DifferentEntries,
    DuplicateEntry,
    Entry,
    PathPoint,
    UnknownCapability,
    compare_stop_policies,
    fingerprint,
    require_same_entries,
    visible_path,
)
from channelflow.stops import AnchorKind, CostModel, PositionState, StopAnchor

SECOND = 1_000_000_000
STEP = 600 * SECOND
FLOOR = 0.05
FREE = CostModel(taker_fee_bps=Decimal(0), slippage_bps=Decimal(0))


def position(index: int) -> PositionState:
    """Entry 100, initial stop 98, target 112. R0 = 2."""
    return PositionState(
        position_id=uuid.UUID(int=index),
        instrument_id="BTCUSDT",
        side="LONG",
        quantity=Decimal(1),
        entry_time_ns=0,
        average_entry_price=Decimal(100),
        initial_stop_price=Decimal(98),
        current_strategy_stop=Decimal(98),
        original_target_price=Decimal(112),
    )


def path(
    prices: list[float],
    *,
    noise: str = "0.40",
    order_flow_veto: tuple[int, ...] = (),
    forecast_veto: tuple[int, ...] = (),
    defi_veto: tuple[int, ...] = (),
) -> tuple[PathPoint, ...]:
    """Every point carries a swing anchor 1.2 below and a channel one 1.0 below.

    The channel anchor is the tighter of the two, which is what makes the
    channel-conditioned arm trail closer than the swing arm — and, on a path
    with a shakeout in it, get stopped where the swing arm survives.
    """
    built = []
    for index, value in enumerate(prices):
        at_ns = (index + 1) * STEP
        price = Decimal(str(round(value, 4)))
        built.append(
            PathPoint(
                at_ns=at_ns,
                price=price,
                noise_distance=Decimal(noise),
                anchors=(
                    StopAnchor(
                        kind=AnchorKind.CONFIRMED_SWING,
                        price=price - Decimal("1.2"),
                        known_at_ns=at_ns,
                        description="swing",
                    ),
                    StopAnchor(
                        kind=AnchorKind.CHANNEL_BOUNDARY,
                        price=price - Decimal("1.0"),
                        known_at_ns=at_ns,
                        description="channel",
                    ),
                ),
                order_flow_confirms=index not in order_flow_veto,
                turning_forecast_permits=index not in forecast_veto,
                defi_context_permits=index not in defi_veto,
            )
        )
    return tuple(built)


def two_shakeouts() -> tuple[list[float], int, int]:
    """Rise, a dip that takes out a stop trailing 1.6 below, recover, and again.

    A stop tightened at bar `k` sits at `price[k] - 1.6`; the next bar falls
    1.7, so it is hit. A policy that *held* at bar `k` still has the stop from
    bar `k - 1`, at `price[k] - 2.2`, and survives. That is what makes a veto
    worth something here, and it is the only reason the arms differ at all.
    """
    prices: list[float] = []
    level = 100.0
    for _ in range(10):
        prices.append(level)
        level += 0.6
    first = len(prices) - 1
    prices.append(prices[-1] - 1.7)
    prices.append(prices[first])
    level = prices[-1] + 0.6
    for _ in range(8):
        prices.append(level)
        level += 0.6
    second = len(prices) - 1
    prices.append(prices[-1] - 1.7)
    prices.append(prices[second])
    level = prices[-1] + 0.6
    for _ in range(8):
        prices.append(level)
        level += 0.6
    top = prices[-1]
    prices.extend(top - 1.2 * step for step in range(1, 20))
    return prices, first, second


#: Half the entries sit fractionally above the other half's volatility, so the
#: median split has two sides to report. The gap is small on purpose: a
#: difference large enough to move a stop across the shakeout would make the
#: regime split and the ladder measure each other.
QUIET, BUSY = "0.40", "0.41"


def edge_entries(n: int = 8) -> list[Entry]:
    """Each shakeout vetoed by a different capability, so the arms form a ladder."""
    prices, first, second = two_shakeouts()
    return [
        Entry(
            position(i),
            path(
                prices,
                noise=QUIET if i % 2 else BUSY,
                order_flow_veto=(first,),
                forecast_veto=(second,),
            ),
        )
        for i in range(1, n + 1)
    ]


def plain_trend_entries(n: int = 8) -> list[Entry]:
    """No shakeout, so nothing the engine's extra machinery can save."""
    prices = [100 + 0.6 * k for k in range(24)]
    prices += [prices[-1] - 1.2 * k for k in range(1, 18)]
    return [
        Entry(position(i), path(prices, noise=QUIET if i % 2 else BUSY)) for i in range(1, n + 1)
    ]


def run(entries: list[Entry] | None = None, **kwargs: object):
    return compare_stop_policies(
        entries if entries is not None else edge_entries(),
        costs=CostModel(),
        improvement_floor=FLOOR,
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.trace("REQ-EXP-017")
def test_all_seven_policies_the_prd_names_are_compared() -> None:
    """Fixed initial stop; naive fixed-percent trailing; ATR/volatility
    trailing; confirmed-swing structural; channel-conditioned; structural plus
    order-flow confirmation; the full engine."""
    assert POLICIES == (
        "fixed_initial_stop",
        "naive_fixed_percent",
        "atr_trailing",
        "confirmed_swing_structural",
        "channel_conditioned",
        "structural_plus_order_flow",
        ENGINE,
    )

    report = run()

    assert list(report.policies) == list(POLICIES)


@pytest.mark.trace("REQ-EXP-017")
def test_every_primary_metric_the_prd_names_is_reported() -> None:
    """Twelve of them, because a stop policy has no single score."""
    assert len(METRICS) == 12

    metrics = run().policies[ENGINE]

    assert metrics.expectancy_r is not None
    assert metrics.median_r is not None
    assert metrics.stop_out_rate is not None
    assert metrics.premature_stop_rate is not None
    assert metrics.give_back_r is not None
    assert metrics.mae_r is not None
    assert metrics.median_stop_distance_r is not None
    assert metrics.p95_stop_distance_r is not None
    assert metrics.average_holding_ns is not None
    assert metrics.average_stop_updates is not None
    assert metrics.worst_r is not None
    assert metrics.worst_slippage_bps is not None
    assert metrics.regime.spread is not None


@pytest.mark.trace("REQ-EXP-017")
def test_the_premature_stop_rate_cannot_be_read_without_realized_expectancy() -> None:
    """PRD section 44A.29 in as many words: "an infinitely wide stop would make
    it look good while destroying risk control. Always combine with realized
    expectancy and downside metrics."

    A property on the object that carries expectancy is how that stops being
    advice.
    """
    metrics = run().policies[ENGINE]

    assert "premature_stop_rate" not in {field for field in metrics.__dataclass_fields__}, (
        "a field could be lifted out on its own"
    )
    assert metrics.premature_stop_rate is not None
    assert metrics.expectancy_r is not None


@pytest.mark.trace("REQ-EXP-017")
def test_a_policy_that_never_stopped_out_has_no_premature_rate() -> None:
    """A rate over no stop-outs is not zero, and a policy that never stopped has
    not earned a perfect score on this."""
    calm = [Entry(position(1), path([100 + 0.6 * k for k in range(12)]))]

    metrics = run(calm).policies["fixed_initial_stop"]

    assert metrics.stopped_out == 0
    assert metrics.premature_stop_rate is None


@pytest.mark.trace("REQ-EXP-017")
def test_all_seven_ablations_the_prd_names_are_run() -> None:
    """Remove swing confirmation; volatility/noise floor; order-flow veto;
    channel context; extremum/turning-point forecast; DeFi/cross-venue context;
    hysteresis/cooldown."""
    assert ABLATIONS == (
        "swing_confirmation",
        "volatility_noise_floor",
        "order_flow_veto",
        "channel_context",
        "turning_point_forecast",
        "defi_cross_venue_context",
        "hysteresis_cooldown",
    )

    report = run()

    assert list(report.ablations) == list(ABLATIONS)
    for name, ablation in report.ablations.items():
        assert ablation.capability == name
        assert ablation.expectancy_delta is not None


@pytest.mark.trace("REQ-EXP-017")
def test_an_ablation_can_come_out_either_way() -> None:
    """Removing a capability does not have to hurt, and here one of them helps.

    On the shakeout fixture the order-flow veto is worth several R: it is what
    keeps the stop from tightening into the dip. On a clean trend the noise
    floor is worth less than nothing — the buffer widens the stop and the wider
    stop exits later on the way down. An experiment that assumed every
    capability helps would have nowhere to put the second number.
    """
    shaken = run().ablations
    trending = run(plain_trend_entries()).ablations

    assert shaken["order_flow_veto"].expectancy_delta is not None
    assert shaken["order_flow_veto"].expectancy_delta > 0.0
    assert trending["volatility_noise_floor"].expectancy_delta is not None
    assert trending["volatility_noise_floor"].expectancy_delta < 0.0


@pytest.mark.trace("REQ-EXP-017")
def test_an_engine_that_earns_its_complexity_is_accepted() -> None:
    """The control. Without it, `NO_EDGE` everywhere would be consistent with an
    experiment that cannot accept anything."""
    report = run()

    assert report.verdict == EDGE
    assert report.policies[ENGINE].expectancy_r is not None
    # The engine is not one of the six it has to beat. Counting it among its own
    # rivals makes it the best of them by construction, and the margin zero.
    best = report.best_simpler_policy
    assert best is not None and best != ENGINE
    rivals = {
        name: metrics.expectancy_r
        for name, metrics in report.policies.items()
        if name != ENGINE and metrics.expectancy_r is not None
    }
    assert best == max(rivals, key=lambda name: rivals[name])
    assert report.policies[ENGINE].expectancy_r > rivals[best]


@pytest.mark.trace("REQ-EXP-017")
def test_an_engine_that_only_looks_better_is_rejected() -> None:
    """EXP-017's own last paragraph.

    On a path with no shakeout there is nothing for the engine's extra
    machinery to save, and a simpler trailing stop keeps more. The engine is the
    arm everybody wants to keep, so the burden is on it.
    """
    report = run(plain_trend_entries())

    assert report.verdict == NO_EDGE
    assert "only looks better is rejected" in report.reason


@pytest.mark.trace("REQ-EXP-017")
def test_the_floor_decides_the_verdict() -> None:
    """And it is the floor doing it, not the data: the same entries accept the
    engine at a five-hundredth of an R and reject it at half an R."""
    entries = edge_entries()

    lenient = compare_stop_policies(entries, costs=CostModel(), improvement_floor=FLOOR)
    strict = compare_stop_policies(entries, costs=CostModel(), improvement_floor=0.5)

    assert lenient.verdict == EDGE
    assert strict.verdict == NO_EDGE


@pytest.mark.trace("REQ-EXP-017")
def test_every_policy_runs_over_the_exact_same_entry_signals() -> None:
    """EXP-017's own words.

    A stop study that let each policy pick its own entries would be comparing
    entry selection and attributing the difference to stop management.
    """
    entries = edge_entries()

    report = run(entries)

    assert report.fingerprint == fingerprint(entries)
    for metrics in report.policies.values():
        assert metrics.trades == len(entries)


@pytest.mark.trace("REQ-EXP-017")
def test_reports_over_different_entries_cannot_be_compared() -> None:
    here = run(edge_entries())
    elsewhere = run(edge_entries(n=6))

    require_same_entries([here, here])
    with pytest.raises(DifferentEntries):
        require_same_entries([here, elsewhere])


@pytest.mark.trace("REQ-EXP-017")
def test_the_same_signal_twice_is_refused() -> None:
    """It would weight that signal double in every policy's metrics, which is a
    fact about the input and reads as a fact about the policies."""
    doubled = [*edge_entries(n=2), Entry(position(1), path([100.0, 99.0, 98.0]))]

    with pytest.raises(DuplicateEntry):
        run(doubled)


@pytest.mark.trace("REQ-EXP-017")
def test_a_capability_the_engine_does_not_have_is_refused() -> None:
    with pytest.raises(UnknownCapability, match="vibes"):
        Capabilities().without("vibes")


@pytest.mark.trace("REQ-EXP-017")
def test_a_capability_that_is_off_neither_vetoes_nor_supplies_a_level() -> None:
    """Which is why an ablation changes the path rather than the policy's code.

    An ablation implemented as a branch inside the policy would be a second
    policy that only looked like the first.
    """
    shape = path([100.0, 100.6], order_flow_veto=(1,))

    with_everything = visible_path(shape, Capabilities())
    without_channel = visible_path(shape, Capabilities().without("channel_context"))
    without_swing = visible_path(shape, Capabilities().without("swing_confirmation"))
    without_veto = visible_path(shape, Capabilities().without("order_flow_veto"))
    without_floor = visible_path(shape, Capabilities().without("volatility_noise_floor"))

    assert {a.kind for a in with_everything[0].anchors} == {
        AnchorKind.CONFIRMED_SWING,
        AnchorKind.CHANNEL_BOUNDARY,
    }
    assert {a.kind for a in without_channel[0].anchors} == {AnchorKind.CONFIRMED_SWING}
    assert {a.kind for a in without_swing[0].anchors} == {AnchorKind.CHANNEL_BOUNDARY}
    # The veto is what empties the second point, and removing the veto restores it.
    assert with_everything[1].anchors == ()
    assert without_veto[1].anchors != ()
    assert without_floor[0].noise_distance == Decimal(0)


@pytest.mark.trace("REQ-EXP-017")
def test_a_path_that_never_stopped_is_marked_out_rather_than_dropped() -> None:
    """A policy that never exits has no losses and would win every comparison.

    Marked out at the last observed price, and not charged a stop's adverse
    slippage, because it did not pay one.
    """
    calm = [Entry(position(1), path([100 + 0.6 * k for k in range(12)]))]

    def priced(costs: CostModel) -> float | None:
        return (
            compare_stop_policies(calm, costs=costs, improvement_floor=FLOOR)
            .policies["fixed_initial_stop"]
            .expectancy_r
        )

    free = priced(FREE)
    assert free == pytest.approx((100 + 0.6 * 11 - 100) / 2)

    # A stop's adverse slippage does not apply: charging it would bill a
    # position that never hit its stop for hitting it.
    assert priced(CostModel(taker_fee_bps=Decimal(0), slippage_bps=Decimal(100))) == (
        pytest.approx(free)
    )

    # The taker fee does apply: it is still an exit, and one that pays.
    charged = priced(CostModel(taker_fee_bps=Decimal(100), slippage_bps=Decimal(0)))
    assert charged is not None and free is not None
    assert charged < free


@pytest.mark.trace("REQ-EXP-017")
def test_the_improvement_floor_is_required_and_positive() -> None:
    with pytest.raises(TypeError):
        compare_stop_policies(edge_entries(), costs=CostModel())  # type: ignore[call-arg]

    with pytest.raises(ValueError, match="improvement_floor"):
        compare_stop_policies(edge_entries(), costs=CostModel(), improvement_floor=0.0)


@pytest.mark.trace("REQ-EXP-017")
def test_two_runs_produce_equal_reports() -> None:
    entries = edge_entries()

    first = run(entries)
    second = run(entries)

    assert first.policies == second.policies
    assert first.ablations == second.ablations
    assert first.verdict == second.verdict


@pytest.mark.trace("REQ-EXP-017")
def test_a_policy_that_never_lost_has_no_profit_factor() -> None:
    """Dividing by zero losses gives infinity, which reads as a spectacular
    result rather than as a sample with nothing to divide by."""
    metrics = run().policies[ENGINE]

    assert metrics.worst_r is not None and metrics.worst_r > 0.0, "nothing lost here"
    assert metrics.profit_factor is None


@pytest.mark.trace("REQ-EXP-017")
def test_the_stop_distance_quantiles_are_two_different_numbers() -> None:
    """Section 44A asks for the median *and* the 95th percentile, and the pair
    is the point: a stop that is usually close and occasionally very far is a
    different policy from one that is always at its median distance.

    A fixed stop on a rising path is the clearest case — the distance grows
    every bar — so its two quantiles cannot coincide.
    """
    metrics = run().policies["fixed_initial_stop"]

    assert metrics.median_stop_distance_r is not None
    assert metrics.p95_stop_distance_r is not None
    assert metrics.p95_stop_distance_r > metrics.median_stop_distance_r
