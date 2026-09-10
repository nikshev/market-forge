"""EXP-017: whether an adaptive stop engine earns what it costs.

# @trace: REQ-EXP-017

    Compare position-management policies on the exact same immutable entry
    signals: fixed initial stop only; naive fixed-percent trailing;
    ATR/volatility trailing; confirmed-swing structural trailing;
    channel-conditioned structural stop; structural stop + order-flow
    confirmation; full Adaptive Stop Management Engine.

    ... The experiment must be able to conclude `NO_EDGE`: a sophisticated
    trailing policy is rejected if it only looks better visually but does not
    improve OOS economics or risk-adjusted outcomes.

Three phrases in that requirement do the work.

**"The exact same immutable entry signals."** Every policy replays the same
positions over the same paths. A stop study that let each policy pick its own
entries would be comparing entry selection, and the difference would be
attributed to stop management. The entries carry a fingerprint so that two
reports cannot be put in one table without the comparison being checkable.

**Twelve primary metrics**, because a stop policy has no single score. Widening
a stop lowers the stop-out rate, lowers the premature-stop rate, raises the
average holding time, raises the give-back and eventually destroys risk control
-- PRD section 44A.29 says so in as many words, which is why the premature-stop
rate here is a property of an object that also carries realized expectancy and
cannot be read without it.

**`NO_EDGE`.** The engine is the interesting arm and the one everybody wants to
keep. So the verdict compares it against the best of the six simpler policies on
the same entries, after costs, and rejects it when the margin is not there.

The seven ablations are the same machinery: the full engine with one capability
switched off, replayed over the same entries. Some of them make the engine
tighten *more* often -- removing the order-flow veto removes a reason to hold --
and some make it tighten less. Both are real and the report does not assume
which.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal
from statistics import fmean, median

from channelflow.experiments import ConfigValue, Field
from channelflow.stops import (
    AnchorKind,
    CostModel,
    NaiveATRTrailing,
    NaiveFixedPercent,
    PositionState,
    PricePoint,
    Replay,
    StopAnchor,
    StopPolicy,
    StopPolicyOutcome,
)

#: EXP-017's seven policies, in the PRD's order.
POLICIES: tuple[str, ...] = (
    "fixed_initial_stop",
    "naive_fixed_percent",
    "atr_trailing",
    "confirmed_swing_structural",
    "channel_conditioned",
    "structural_plus_order_flow",
    "full_engine",
)

#: The arm the other six exist to test.
ENGINE = "full_engine"

#: EXP-017's seven ablations, in the PRD's order. Each names a capability the
#: full engine has; the ablation is the engine without it.
ABLATIONS: tuple[str, ...] = (
    "swing_confirmation",
    "volatility_noise_floor",
    "order_flow_veto",
    "channel_context",
    "turning_point_forecast",
    "defi_cross_venue_context",
    "hysteresis_cooldown",
)

#: EXP-017's twelve primary metrics, in the PRD's order. Named so a report can
#: be checked against the list rather than against whatever it happens to carry.
METRICS: tuple[str, ...] = (
    "expectancy_after_costs",
    "realized_r_multiple",
    "profit_factor",
    "stop_out_rate",
    "premature_stop_rate",
    "give_back_from_mfe",
    "mae_before_stop",
    "stop_distance_median_and_p95",
    "average_holding_time",
    "stop_modification_count",
    "tail_loss_and_worst_slippage",
    "regime_stability",
)

EDGE = "edge"
NO_EDGE = "no_edge"


class UnknownCapability(ValueError):
    """An ablation names a capability the engine does not have."""


class DuplicateEntry(ValueError):
    """Two entries share a position id, so they are not one set of signals."""


class DifferentEntries(ValueError):
    """Two reports were run over different entry signals."""


@dataclass(frozen=True)
class Capabilities:
    """Which parts of the full engine are switched on.

    One flag per ablation EXP-017 names, so an ablation is `without(name)` and
    cannot drift from the list.
    """

    swing_confirmation: bool = True
    volatility_noise_floor: bool = True
    order_flow_veto: bool = True
    channel_context: bool = True
    turning_point_forecast: bool = True
    defi_cross_venue_context: bool = True
    hysteresis_cooldown: bool = True

    def without(self, capability: str) -> Capabilities:
        if capability not in ABLATIONS:
            raise UnknownCapability(
                f"{capability!r} is not one of EXP-017's capabilities ({', '.join(ABLATIONS)})"
            )
        return replace(self, **{capability: False})


@dataclass(frozen=True)
class PathPoint:
    """One decision instant, with the context each ablation switches off.

    A superset of the replay's `PricePoint`: the three context flags are what
    the order-flow veto, the turning-point forecast and the cross-venue view
    each contribute, expressed as permission to tighten rather than as another
    anchor. A veto is not a level.
    """

    at_ns: int
    price: Decimal
    noise_distance: Decimal
    anchors: tuple[StopAnchor, ...] = ()
    data_quality_ok: bool = True
    order_flow_confirms: bool = True
    turning_forecast_permits: bool = True
    defi_context_permits: bool = True


@dataclass(frozen=True)
class Entry:
    """One immutable entry signal and the path that followed it."""

    position: PositionState
    path: tuple[PathPoint, ...]


@dataclass(frozen=True)
class EntryFingerprint:
    """Enough of an entry set to tell two of them apart."""

    entries: int
    ids: tuple[str, ...]


@dataclass(frozen=True)
class RegimeSplit:
    """Expectancy either side of the entry set's own median volatility.

    The split is the median of the paths' own average noise distance, so it
    halves any sample. A cut taken from one path's reading lands wherever that
    path happened to be.
    """

    quiet_trades: int
    busy_trades: int
    quiet_expectancy_r: float | None
    busy_expectancy_r: float | None

    @property
    def spread(self) -> float | None:
        """How far apart the two regimes are. Smaller is more stable.

        Not a ratio: expectancy is signed, and a ratio of two signed numbers
        changes meaning as either crosses zero.
        """
        if self.quiet_expectancy_r is None or self.busy_expectancy_r is None:
            return None
        return abs(self.quiet_expectancy_r - self.busy_expectancy_r)


@dataclass(frozen=True)
class PolicyMetrics:
    """EXP-017's twelve primary metrics for one policy.

    `premature_stop_rate` is a property rather than a field, on an object that
    also carries `expectancy_r` -- PRD section 44A.29's warning made structural:
    "an infinitely wide stop would make it look good while destroying risk
    control. Always combine with realized expectancy and downside metrics."
    """

    policy: str
    trades: int
    stopped_out: int
    premature_stops: int
    expectancy_r: float | None
    median_r: float | None
    profit_factor: float | None
    stop_out_rate: float | None
    give_back_r: float | None
    mae_r: float | None
    median_stop_distance_r: float | None
    p95_stop_distance_r: float | None
    average_holding_ns: float | None
    average_stop_updates: float | None
    worst_r: float | None
    worst_slippage_bps: float | None
    regime: RegimeSplit

    @property
    def premature_stop_rate(self) -> float | None:
        """Of the positions stopped out, how many later reached their target.

        `None` over no stop-outs: a rate over nothing is not zero, and a policy
        that never stopped out has not earned a perfect score on this.
        """
        if not self.stopped_out:
            return None
        return self.premature_stops / self.stopped_out


@dataclass(frozen=True)
class Ablation:
    """The engine without one capability, against the engine with it."""

    capability: str
    metrics: PolicyMetrics
    #: Engine minus ablation. Positive means the capability was worth something.
    expectancy_delta: float | None


@dataclass(frozen=True)
class StopComparison:
    """EXP-017's seven policies, seven ablations, and the verdict."""

    policies: dict[str, PolicyMetrics]
    ablations: dict[str, Ablation]
    fingerprint: EntryFingerprint
    improvement_floor: float
    verdict: str
    reason: str
    configs: dict[str, Mapping[str, ConfigValue]] = field(default_factory=dict)

    @property
    def best_simpler_policy(self) -> str | None:
        """The strongest of the six the engine has to beat."""
        scored = [
            (name, metrics.expectancy_r)
            for name, metrics in self.policies.items()
            if name != ENGINE and metrics.expectancy_r is not None
        ]
        if not scored:
            return None
        return max(scored, key=lambda pair: (pair[1], pair[0]))[0]

    @property
    def compared(self) -> Field:
        """The seven policies replayed over the same entries, and the engine when
        it earned promotion.

        `chosen` is the engine only on an `edge` verdict. EXP-017 puts the
        burden on the engine -- it has to beat the best of the six simpler
        policies by the floor -- so a `no_edge` run chose nothing, and recording
        the engine as kept there would report a promotion that did not happen.
        """
        return Field(variants=self.configs, chosen=ENGINE if self.verdict == EDGE else None)


def fingerprint(entries: Sequence[Entry]) -> EntryFingerprint:
    """The entry signals a report was run over, so two reports can be compared."""
    return EntryFingerprint(
        entries=len(entries), ids=tuple(str(e.position.position_id) for e in entries)
    )


def require_same_entries(reports: Sequence[StopComparison]) -> None:
    """Refuse a comparison across reports run on different entries.

    EXP-017's own words are "the exact same immutable entry signals". Two stop
    studies over different entries differ by their entries as much as by their
    stops, and nothing about the numbers says which.
    """
    prints = {report.fingerprint for report in reports}
    if len(prints) > 1:
        raise DifferentEntries(
            f"{len(reports)} report(s) carry {len(prints)} different entry sets; the "
            "difference between them is the difference between the entries as much "
            "as between the policies"
        )


#: What each of the six structural policies can see. The naive two and the fixed
#: stop are not configurations of the engine at all.
POLICY_CAPABILITIES: dict[str, Capabilities] = {
    "confirmed_swing_structural": Capabilities(
        channel_context=False,
        order_flow_veto=False,
        turning_point_forecast=False,
        defi_cross_venue_context=False,
    ),
    "channel_conditioned": Capabilities(
        order_flow_veto=False,
        turning_point_forecast=False,
        defi_cross_venue_context=False,
    ),
    "structural_plus_order_flow": Capabilities(
        turning_point_forecast=False,
        defi_cross_venue_context=False,
    ),
    ENGINE: Capabilities(),
}


def visible_path(path: Sequence[PathPoint], capabilities: Capabilities) -> list[PricePoint]:
    """What a policy with these capabilities actually sees.

    A capability the engine does not have cannot veto and cannot supply a level,
    so switching one off changes the path rather than the policy's code. That is
    what keeps every arm on one decision loop: an ablation implemented as a
    branch inside the policy would be a second policy that only looked like the
    first.
    """
    built: list[PricePoint] = []
    for point in path:
        anchors = tuple(
            anchor
            for anchor in point.anchors
            if not (
                anchor.kind is AnchorKind.CONFIRMED_SWING and not capabilities.swing_confirmation
            )
            and not (
                anchor.kind is AnchorKind.CHANNEL_BOUNDARY and not capabilities.channel_context
            )
        )
        vetoed = (
            (capabilities.order_flow_veto and not point.order_flow_confirms)
            or (capabilities.turning_point_forecast and not point.turning_forecast_permits)
            or (capabilities.defi_cross_venue_context and not point.defi_context_permits)
        )
        built.append(
            PricePoint(
                at_ns=point.at_ns,
                price=point.price,
                # A noise floor the engine does not have is not a floor of zero
                # somewhere else: the buffer simply does not apply.
                noise_distance=(
                    point.noise_distance if capabilities.volatility_noise_floor else Decimal(0)
                ),
                anchors=() if vetoed else anchors,
                data_quality_ok=point.data_quality_ok,
            )
        )
    return built


def policy_for(capabilities: Capabilities) -> StopPolicy:
    """The engine configured for these capabilities.

    Hysteresis is the one capability that lives in the policy's own fields
    rather than in what it can see: without it there is no cooldown and no
    improvement threshold, so every proposal that tightens at all is taken.
    """
    if capabilities.hysteresis_cooldown:
        return StopPolicy()
    return StopPolicy(min_improvement_bps=Decimal(0), cooldown_ns=0)


def compare_stop_policies(
    entries: Sequence[Entry],
    *,
    costs: CostModel,
    improvement_floor: float,
    policies: Sequence[str] = POLICIES,
    ablations: Sequence[str] = ABLATIONS,
) -> StopComparison:
    """Replay every policy over the same entries, then ablate the engine.

    `improvement_floor` has no default. It decides how much better than the best
    simpler policy the engine has to be before the answer is `EDGE`, and it is
    the number the whole verdict turns on (PRD section 13A.27).
    """
    if improvement_floor <= 0.0:
        raise ValueError(
            "improvement_floor must be positive; a floor of zero accepts any margin "
            "at all, which is how a policy that is not better gets kept"
        )
    if not entries:
        raise ValueError("there is nothing to compare over no entry signals")
    ids = [e.position.position_id for e in entries]
    if len(set(ids)) != len(ids):
        raise DuplicateEntry(
            "two entries share a position id; the same signal counted twice weights "
            "it double in every policy's metrics"
        )
    unknown = [name for name in policies if name not in POLICIES]
    if unknown:
        raise ValueError(
            f"{', '.join(unknown)} is not one of EXP-017's policies ({', '.join(POLICIES)})"
        )

    replay = Replay(costs=costs)
    scored = {
        name: _metrics(name, [_run(name, entry, replay) for entry in entries], entries, costs)
        for name in policies
    }
    ablated = {
        name: _ablation(name, entries, replay, costs, scored.get(ENGINE)) for name in ablations
    }
    verdict, reason = _rule(scored, improvement_floor)
    return StopComparison(
        policies=scored,
        ablations=ablated,
        fingerprint=fingerprint(entries),
        improvement_floor=improvement_floor,
        verdict=verdict,
        reason=reason,
        configs={
            name: {"policy": name, "improvement_floor": improvement_floor} for name in policies
        },
    )


def _run(name: str, entry: Entry, replay: Replay) -> StopPolicyOutcome:
    """One policy over one entry, always through the same replay loop."""
    if name == "fixed_initial_stop":
        # No anchor is ever knowable, so the engine holds on every instant and
        # the stop stays where it started. Running it through the same loop --
        # rather than special-casing the exit -- is what makes its costs, its
        # excursion and its holding time comparable with the others'.
        blind = [replace(point, anchors=()) for point in entry.path]
        return replay.run_adaptive(
            entry.position, visible_path(blind, Capabilities()), StopPolicy()
        )
    if name == "naive_fixed_percent":
        return replay.run_naive(
            entry.position, visible_path(entry.path, Capabilities()), NaiveFixedPercent()
        )
    if name == "atr_trailing":
        return replay.run_naive(
            entry.position, visible_path(entry.path, Capabilities()), NaiveATRTrailing()
        )
    capabilities = POLICY_CAPABILITIES[name]
    return replay.run_adaptive(
        entry.position, visible_path(entry.path, capabilities), policy_for(capabilities)
    )


def _ablation(
    capability: str,
    entries: Sequence[Entry],
    replay: Replay,
    costs: CostModel,
    engine: PolicyMetrics | None,
) -> Ablation:
    reduced = Capabilities().without(capability)
    outcomes = [
        replay.run_adaptive(entry.position, visible_path(entry.path, reduced), policy_for(reduced))
        for entry in entries
    ]
    metrics = _metrics(f"{ENGINE}_without_{capability}", outcomes, entries, costs)
    delta = (
        None
        if engine is None or engine.expectancy_r is None or metrics.expectancy_r is None
        else engine.expectancy_r - metrics.expectancy_r
    )
    return Ablation(capability=capability, metrics=metrics, expectancy_delta=delta)


def _realized(outcome: StopPolicyOutcome, entry: Entry, costs: CostModel) -> float | None:
    """The R this position finished at, stopped or not.

    A path that never stopped is marked out at its last observed price. Leaving
    it unpriced would let a policy that never exits report no losses and win
    every comparison; charging it a stop's adverse slippage would be worse
    still, because it did not pay one.
    """
    if outcome.realized_r is not None:
        return outcome.realized_r
    if not entry.path:
        return None
    position = entry.position
    last = entry.path[-1].price
    gross = (
        last - position.average_entry_price
        if position.side == "LONG"
        else position.average_entry_price - last
    )
    fees = costs.fees(last, position.quantity)
    per_unit = fees / position.quantity if position.quantity else Decimal(0)
    return float((gross - per_unit) / position.initial_risk_per_unit)


def _metrics(
    name: str,
    outcomes: Sequence[StopPolicyOutcome],
    entries: Sequence[Entry],
    costs: CostModel,
) -> PolicyMetrics:
    """EXP-017's twelve, over one policy's replay of every entry."""
    returns = [_realized(o, e, costs) for o, e in zip(outcomes, entries, strict=True)]
    priced = [r for r in returns if r is not None]
    stopped = [o for o in outcomes if o.exited]
    wins = [r for r in priced if r > 0.0]
    losses = [r for r in priced if r < 0.0]
    distances = [d for o in outcomes for d in o.stop_distances_r]
    give_backs = [
        o.mfe_r - r
        for o, r in zip(outcomes, returns, strict=True)
        if o.mfe_r is not None and r is not None
    ]
    holdings = [float(o.holding_ns) for o in outcomes if o.holding_ns is not None]
    maes = [o.mae_r for o in outcomes if o.mae_r is not None]

    return PolicyMetrics(
        policy=name,
        trades=len(outcomes),
        stopped_out=len(stopped),
        premature_stops=sum(1 for o in stopped if o.reached_target_after_stop),
        expectancy_r=fmean(priced) if priced else None,
        median_r=median(priced) if priced else None,
        # `None` when nothing lost: dividing by zero losses gives infinity,
        # which reads as a spectacular result rather than as a sample with
        # nothing to divide by.
        profit_factor=(sum(wins) / abs(sum(losses))) if losses else None,
        stop_out_rate=(len(stopped) / len(outcomes)) if outcomes else None,
        give_back_r=fmean(give_backs) if give_backs else None,
        mae_r=fmean(maes) if maes else None,
        median_stop_distance_r=median(distances) if distances else None,
        p95_stop_distance_r=_quantile(distances, 0.95),
        average_holding_ns=fmean(holdings) if holdings else None,
        average_stop_updates=fmean([float(o.stop_updates) for o in outcomes]) if outcomes else None,
        worst_r=min(priced) if priced else None,
        worst_slippage_bps=max((o.stop_slippage_bps for o in stopped), default=None),
        regime=_regimes(outcomes, entries, returns),
    )


def _quantile(values: Sequence[float], q: float) -> float | None:
    """The `q`th value of the sorted sample, by nearest rank.

    Nearest rank rather than interpolation: a 95th percentile of stop distances
    is meant to name a distance that actually occurred.
    """
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, min(len(ordered), int(round(q * len(ordered)))))
    return ordered[rank - 1]


def _regimes(
    outcomes: Sequence[StopPolicyOutcome],
    entries: Sequence[Entry],
    returns: Sequence[float | None],
) -> RegimeSplit:
    """Expectancy either side of the entry set's own median volatility."""
    del outcomes
    volatilities = [
        fmean([float(p.noise_distance) for p in entry.path]) if entry.path else 0.0
        for entry in entries
    ]
    if not volatilities:
        return RegimeSplit(0, 0, None, None)
    cut = median(volatilities)
    quiet = [r for r, v in zip(returns, volatilities, strict=True) if v <= cut and r is not None]
    busy = [r for r, v in zip(returns, volatilities, strict=True) if v > cut and r is not None]
    return RegimeSplit(
        quiet_trades=len(quiet),
        busy_trades=len(busy),
        quiet_expectancy_r=fmean(quiet) if quiet else None,
        busy_expectancy_r=fmean(busy) if busy else None,
    )


EXPERIMENT = "EXP-017"

#: The comparison this module's entry point returns.
COMPARISON = StopComparison


def _rule(policies: dict[str, PolicyMetrics], floor: float) -> tuple[str, str]:
    """EXP-017's own last paragraph, made mechanical.

    The engine is the arm everybody wants to keep, so the burden is on it: it
    has to beat the best of the six simpler policies by the floor, on the same
    entries, after costs.
    """
    engine = policies.get(ENGINE)
    if engine is None or engine.expectancy_r is None:
        return NO_EDGE, "the full engine was not scored, so there is nothing to accept"
    rivals = {
        name: metrics.expectancy_r
        for name, metrics in policies.items()
        if name != ENGINE and metrics.expectancy_r is not None
    }
    if not rivals:
        return NO_EDGE, "no simpler policy was scored, so the engine has nothing to beat"
    best = max(rivals, key=lambda name: (rivals[name], name))
    margin = engine.expectancy_r - rivals[best]
    if margin < floor:
        return (
            NO_EDGE,
            f"the engine adds {margin:+.4f}R over {best} after costs, under the "
            f"{floor:.4f}R the experiment requires; a policy that only looks better "
            "is rejected",
        )
    return EDGE, f"the engine adds {margin:+.4f}R over {best} after costs"
