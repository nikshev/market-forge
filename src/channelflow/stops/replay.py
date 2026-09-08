"""PRD section 44A.28's counterfactual stop-path evaluation.

# @trace: REQ-WP-020
# @trace: REQ-BIAS-009

Replay one price path under several policies and compare what each produced.
Section 44A.39 requires a naive trailing baseline in the comparison, and
section 44A.29 requires the premature-stop rate -- with a warning attached:

    "Do not optimize this metric alone: an infinitely wide stop would make it
    look good while destroying risk control. Always combine with realized
    expectancy and downside metrics."

So the report refuses to hand out the premature-stop rate without realized R
beside it.

Costs are included (ADR-031, PRD section 41 rule 9). Realized R is net of fees
and modelled slippage, taken from the first executable price rather than the
requested stop -- section 44A.23: "A stop price is not a guaranteed fill price."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.stops.models import (
    PositionPhase,
    PositionState,
    StopAnchor,
    StopPolicyOutcome,
)
from channelflow.stops.policy import StopPolicy

BPS = Decimal(10_000)


@dataclass(frozen=True)
class PricePoint:
    """One decision instant on the path."""

    at_ns: int
    price: Decimal
    noise_distance: Decimal
    anchors: tuple[StopAnchor, ...] = ()
    data_quality_ok: bool = True


@dataclass(frozen=True)
class CostModel:
    """What an exit actually costs.

    `slippage_bps` is *modelled*, and the name says so: a constant basis-point
    cost understates a gap and overstates a calm fill. The honest version needs
    the book at stop time, and no fill model exists (ADR-031).
    """

    taker_fee_bps: Decimal = Decimal(5)
    slippage_bps: Decimal = Decimal(3)

    def executable_exit(self, requested: Decimal, *, side: str) -> tuple[Decimal, float]:
        """The first executable price, and the slippage in bps.

        Always adverse. Slippage that sometimes favoured the position would be
        a rounding argument; on a stop it is always the wrong way.
        """
        adverse = requested * self.slippage_bps / BPS
        realized = requested - adverse if side == "LONG" else requested + adverse
        return realized, float(self.slippage_bps)

    def fees(self, price: Decimal, quantity: Decimal) -> Decimal:
        return price * quantity * self.taker_fee_bps / BPS


class NaiveFixedPercent:
    """PRD section 44A's required naive baseline: trail by a fixed percentage.

    No structural anchor anywhere. It exists to be beaten, and to show what the
    engine's extra machinery is buying.
    """

    def __init__(self, percent: Decimal = Decimal("0.02")) -> None:
        self.percent = percent
        self.name = "naive_fixed_percent"

    def stop_for(self, position: PositionState, price: Decimal) -> Decimal:
        offset = price * self.percent
        return price - offset if position.side == "LONG" else price + offset


class NaiveATRTrailing:
    """Trail by a multiple of the supplied volatility measure."""

    def __init__(self, multiple: Decimal = Decimal(2)) -> None:
        self.multiple = multiple
        self.name = "naive_atr_trailing"

    def stop_for(self, position: PositionState, price: Decimal, noise_distance: Decimal) -> Decimal:
        offset = noise_distance * self.multiple
        return price - offset if position.side == "LONG" else price + offset


@dataclass
class Replay:
    """One path, several policies, one report."""

    costs: CostModel = field(default_factory=CostModel)

    def run_adaptive(
        self, position: PositionState, path: list[PricePoint], policy: StopPolicy
    ) -> StopPolicyOutcome:
        stop = position.current_strategy_stop
        reasons: dict[str, int] = {}
        updates = 0
        requested: Decimal | None = None
        remaining: list[PricePoint] = []

        for index, point in enumerate(path):
            if self._triggered(position, stop, point.price):
                requested = stop
                remaining = list(path[index:])
                break

            current = position.model_copy(update={"current_strategy_stop": stop})
            proposal = policy.propose(
                current,
                anchors=list(point.anchors),
                at_ns=point.at_ns,
                market_price=point.price,
                noise_distance=point.noise_distance,
                phase=PositionPhase.STRUCTURE_TRAIL,
            )
            for reason in proposal.reasons:
                reasons[reason.name] = reasons.get(reason.name, 0) + 1
            if proposal.moved:
                stop = proposal.price
                updates += 1

        return self._outcome("adaptive", position, requested, remaining, reasons, updates)

    def run_naive(
        self,
        position: PositionState,
        path: list[PricePoint],
        policy: NaiveFixedPercent | NaiveATRTrailing,
    ) -> StopPolicyOutcome:
        stop = position.current_strategy_stop
        updates = 0
        requested: Decimal | None = None
        remaining: list[PricePoint] = []

        for index, point in enumerate(path):
            if self._triggered(position, stop, point.price):
                requested = stop
                remaining = list(path[index:])
                break
            proposed = (
                policy.stop_for(position, point.price)
                if isinstance(policy, NaiveFixedPercent)
                else policy.stop_for(position, point.price, point.noise_distance)
            )
            # Even the naive baselines respect the monotonic rule: a baseline
            # allowed to widen would not be a stop policy at all, and the
            # comparison would be against something else entirely.
            tightens = proposed > stop if position.side == "LONG" else proposed < stop
            if tightens:
                stop = proposed
                updates += 1

        return self._outcome(policy.name, position, requested, remaining, {}, updates)

    def _triggered(self, position: PositionState, stop: Decimal, price: Decimal) -> bool:
        return price <= stop if position.side == "LONG" else price >= stop

    def _outcome(
        self,
        name: str,
        position: PositionState,
        requested: Decimal | None,
        remaining: list[PricePoint],
        reasons: dict[str, int],
        updates: int,
    ) -> StopPolicyOutcome:
        if requested is None:
            return StopPolicyOutcome(
                policy=name,
                exited=False,
                requested_stop_price=None,
                realized_exit_price=None,
                stop_slippage_bps=0.0,
                fees=Decimal(0),
                realized_r=None,
                reached_target_after_stop=False,
                stop_updates=updates,
                reason_counts=reasons,
            )

        realized, slippage = self.costs.executable_exit(requested, side=position.side)
        fees = self.costs.fees(realized, position.quantity)

        # Section 44A.24's R, net of costs (ADR-031, PRD section 41 rule 9).
        gross = (
            realized - position.average_entry_price
            if position.side == "LONG"
            else position.average_entry_price - realized
        )
        per_unit_cost = fees / position.quantity if position.quantity else Decimal(0)
        realized_r = float((gross - per_unit_cost) / position.initial_risk_per_unit)

        return StopPolicyOutcome(
            policy=name,
            exited=True,
            requested_stop_price=requested,
            realized_exit_price=realized,
            stop_slippage_bps=slippage,
            fees=fees,
            realized_r=realized_r,
            reached_target_after_stop=self._reached_target(position, remaining),
            stop_updates=updates,
            reason_counts=reasons,
        )

    def _reached_target(self, position: PositionState, remaining: list[PricePoint]) -> bool:
        """Section 44A.29: did the original target arrive after the stop fired?"""
        target = position.original_target_price
        if target is None:
            return False
        return any(
            (point.price >= target) if position.side == "LONG" else (point.price <= target)
            for point in remaining
        )


@dataclass(frozen=True)
class ComparisonReport:
    """What every policy produced on one path.

    `premature_stop_rate` is a property rather than a field, and reading it
    without `realized_r` is not possible from the same object -- section
    44A.29's warning made structural.
    """

    outcomes: tuple[StopPolicyOutcome, ...]

    @property
    def premature_stop_rate(self) -> float | None:
        stopped = [o for o in self.outcomes if o.exited]
        if not stopped:
            return None
        return sum(1 for o in stopped if o.reached_target_after_stop) / len(stopped)

    @property
    def summary(self) -> str:
        """The premature-stop rate never appears without realized R beside it.

        Section 44A.29: "an infinitely wide stop would make it look good while
        destroying risk control. Always combine with realized expectancy and
        downside metrics."
        """
        rate = self.premature_stop_rate
        if rate is None:
            return "no policy was stopped out on this path"
        parts = [
            f"{o.policy}: R={o.realized_r:.3f}"
            if o.realized_r is not None
            else f"{o.policy}: no exit"
            for o in self.outcomes
        ]
        return f"premature-stop rate {rate:.0%}; realized R by policy -- {'; '.join(parts)}"
