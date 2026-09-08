"""PRD section 44A.16's stop proposal algorithm.

# @trace: REQ-WP-020

The PRD's own pseudocode is a pipeline of safety filters, and it ends with a
line that is the point of the whole section:

    "No individual feature is allowed to bypass the safety filters."

So the filters run in a fixed order, every one of them can only hold or tighten,
and the last word belongs to the initial-risk contract rather than to whichever
signal was most enthusiastic.

Nothing here reads a clock. Every decision takes the instant it is deciding at,
and every anchor carries the instant it became knowable -- section 44A.3's
`known_at`, which is REQ-WP-019's timestamp doing the job it was built for.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from channelflow.stops.models import (
    AnchorKind,
    PositionPhase,
    PositionState,
    ReasonCode,
    StopAnchor,
    StopProposal,
)

BPS = Decimal(10_000)


@dataclass
class StopPolicy:
    """The default policy: structural anchors, tightening only.

    Every threshold is an argument. PRD section 44A.35 makes the whole engine
    configurable, and Principle X forbids hard-coded trading thresholds.
    """

    #: Section 44A.17's anti-churn: an improvement smaller than this is not
    #: worth an exchange call and the false precision it implies.
    min_improvement_bps: Decimal = Decimal(10)
    #: Section 44A.17's cooldown, in event time.
    cooldown_ns: int = 5 * 60 * 1_000_000_000
    #: Section 44A.8's minimum noise distance, as a multiple of the supplied
    #: volatility measure.
    noise_multiple: Decimal = Decimal("1.5")

    _last_move_ns: int | None = None

    def propose(
        self,
        position: PositionState,
        *,
        anchors: list[StopAnchor],
        at_ns: int,
        market_price: Decimal,
        noise_distance: Decimal,
        phase: PositionPhase,
        data_quality_ok: bool = True,
    ) -> StopProposal:
        """One decision. Always returns a proposal, never `None` (ADR-032)."""
        hold = self._hold(position, at_ns=at_ns, phase=phase)

        if not data_quality_ok:
            # Section 44A.18. Falling back to a price-derived stop here would be
            # the blind following section 44A.39 forbids.
            return hold(ReasonCode.HELD_DATA_QUALITY)

        if self._last_move_ns is not None and at_ns - self._last_move_ns < self.cooldown_ns:
            return hold(ReasonCode.HELD_COOLDOWN)

        # Section 44A.3: no future-confirmed swing before its known_at.
        knowable = [a for a in anchors if a.known_at_ns <= at_ns]
        if not knowable:
            return hold(ReasonCode.HELD_NO_ANCHOR)

        candidate = self._best_anchor(knowable, position=position)
        if candidate is None:
            return hold(ReasonCode.HELD_WOULD_WIDEN)

        buffered = self._apply_noise_buffer(candidate.price, position, noise_distance)
        reasons = [ReasonCode.STRUCTURAL_ANCHOR]
        if buffered != candidate.price:
            reasons.append(ReasonCode.NOISE_BUFFER_APPLIED)

        # Section 44A.2's monotonic rule, applied after the buffer -- a buffer
        # that pushed the stop the wrong way must not sneak past it.
        if not self._tightens(buffered, position):
            return hold(ReasonCode.HELD_WOULD_WIDEN, anchor=candidate)

        if self._beyond_market(buffered, position, market_price):
            return hold(ReasonCode.REFUSED_BEYOND_MARKET, anchor=candidate)

        if self._inside_minimum_distance(buffered, market_price, noise_distance):
            return hold(ReasonCode.HELD_TOO_CLOSE, anchor=candidate)

        if not self._improves_enough(buffered, position):
            return hold(ReasonCode.HELD_BELOW_THRESHOLD, anchor=candidate)

        # Section 44A.16's last filter, and the one nothing may bypass: the
        # accepted initial-risk contract.
        if not self._within_initial_risk(buffered, position):
            return hold(ReasonCode.HELD_WOULD_WIDEN, anchor=candidate)

        self._last_move_ns = at_ns
        return StopProposal(
            price=buffered,
            anchor=candidate,
            reasons=tuple(reasons),
            at_ns=at_ns,
            phase=phase,
        )

    # --- filters ---

    def _hold(
        self, position: PositionState, *, at_ns: int, phase: PositionPhase
    ) -> Callable[..., StopProposal]:
        """A hold factory, so every early return carries the same shape.

        ADR-032: a hold is a proposal, not a `None`, and it carries the anchor
        it considered where one existed.
        """

        def make(reason: ReasonCode, anchor: StopAnchor | None = None) -> StopProposal:
            return StopProposal(
                price=position.current_strategy_stop,
                anchor=anchor,
                reasons=(reason,),
                at_ns=at_ns,
                phase=phase,
            )

        return make

    def _best_anchor(
        self, anchors: list[StopAnchor], *, position: PositionState
    ) -> StopAnchor | None:
        """The tightest anchor that does not widen risk.

        Tightest rather than nearest the market: the point is to protect what
        the position has, and a looser anchor that still tightens is leaving
        risk on the table for no structural reason.
        """
        tightening = [a for a in anchors if self._tightens(a.price, position)]
        if not tightening:
            return None
        if position.side == "LONG":
            return max(tightening, key=lambda a: a.price)
        return min(tightening, key=lambda a: a.price)

    def _tightens(self, price: Decimal, position: PositionState) -> bool:
        if position.side == "LONG":
            return price >= position.current_strategy_stop
        return price <= position.current_strategy_stop

    def _apply_noise_buffer(
        self, price: Decimal, position: PositionState, noise_distance: Decimal
    ) -> Decimal:
        """Section 44A.9: sit clear of the anchor by the noise distance.

        Away from the market, so ordinary noise around the structure does not
        take the position out -- section 44A.29's whole concern.
        """
        buffer = noise_distance * self.noise_multiple
        return price - buffer if position.side == "LONG" else price + buffer

    def _beyond_market(
        self, price: Decimal, position: PositionState, market_price: Decimal
    ) -> bool:
        if position.side == "LONG":
            return price >= market_price
        return price <= market_price

    def _inside_minimum_distance(
        self, price: Decimal, market_price: Decimal, noise_distance: Decimal
    ) -> bool:
        return abs(market_price - price) < noise_distance

    def _improves_enough(self, price: Decimal, position: PositionState) -> bool:
        current = position.current_strategy_stop
        if current == 0:
            return True
        improvement = abs(price - current) / current * BPS
        return improvement >= self.min_improvement_bps

    def _within_initial_risk(self, price: Decimal, position: PositionState) -> bool:
        """The contract nothing may bypass (section 44A.2).

        A tightening stop always satisfies this; the check exists because a
        future policy, a wider buffer, or a mis-signed anchor could produce a
        price that tightens against the *current* stop while sitting outside
        the risk originally accepted.
        """
        if position.side == "LONG":
            return price >= position.initial_stop_price
        return price <= position.initial_stop_price


def swing_anchors(confirmed: list[tuple[Decimal, int]], *, side: str) -> list[StopAnchor]:
    """Confirmed extrema as anchors, carrying their `known_at`.

    Takes `(price, known_at_ns)` pairs rather than `ConfirmedExtremum` so the
    policy has no opinion about where structure comes from -- a channel
    boundary or a volume node arrives the same way.
    """
    kind = AnchorKind.CONFIRMED_SWING
    return [
        StopAnchor(
            kind=kind,
            price=price,
            known_at_ns=known_at,
            description=f"confirmed {'low' if side == 'LONG' else 'high'} at {price}",
        )
        for price, known_at in confirmed
    ]
