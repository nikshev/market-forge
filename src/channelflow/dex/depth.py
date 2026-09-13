"""PRD section 18.7.1's executable liquidity curve.

# @trace: REQ-WP-015

    "Given current active liquidity, traverse initialized ticks above/below
     spot to build the executable liquidity curve... cumulative notional
     required for +/-10/25/50/100 bps."

Within one tick range liquidity is constant, and the amounts follow in closed
form:

    Δx = L * (1/√Pa - 1/√Pb)      token0
    Δy = L * (√Pb - √Pa)          token1

Crossing an initialized tick upward adds its `liquidity_net`; crossing downward
subtracts it. So a depth query is a walk: consume the current range, cross,
consume the next, until the target price is reached or the known liquidity runs
out.

Running out is not a smaller answer (ADR-036). A quote that stopped at 30 bps
when 50 was asked is a liquidity fact, and returning the notional consumed so
far would read as "it costs this much to move the price 50 bps" when it
actually cost that much to exhaust what we know about.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.dex.math import (
    amount0_delta,
    amount1_delta,
    price_from_sqrt_x96,
    price_from_tick,
    sqrt_price,
)
from channelflow.dex.pool import PoolState
from channelflow.dex.reconstruction import require_tick_map_complete

BPS = Decimal(10_000)


@dataclass(frozen=True)
class DepthQuote:
    """What it costs to move the price, or how far we could get.

    `reachable` is the field a caller must read first. When it is false the
    amounts describe exhausting the known liquidity, not reaching the target --
    two different facts that a bare number would conflate (ADR-036).
    """

    reachable: bool
    target_bps: Decimal
    amount0: Decimal
    amount1: Decimal
    reached_bps: Decimal
    ticks_crossed: int
    reason: str = ""


def depth_to_bps(state: PoolState, *, bps: Decimal, upward: bool) -> DepthQuote:
    """Notional required to move the price `bps` in one direction.

    `upward` means token1 in, token0 out -- the price of token0 rising. The
    two directions are computed separately and may differ: concentrated
    liquidity is rarely symmetric, and that asymmetry is the reason a DEX depth
    curve is worth having at all.
    """
    require_tick_map_complete(state)
    if bps < 0:
        raise ValueError("bps must not be negative")
    if state.sqrt_price_x96 <= 0:
        raise ValueError("pool has no price")

    start_price = price_from_sqrt_x96(state.sqrt_price_x96)
    if bps == 0:
        return DepthQuote(
            reachable=True,
            target_bps=bps,
            amount0=Decimal(0),
            amount1=Decimal(0),
            reached_bps=Decimal(0),
            ticks_crossed=0,
        )

    if state.active_liquidity <= 0:
        return DepthQuote(
            reachable=False,
            target_bps=bps,
            amount0=Decimal(0),
            amount1=Decimal(0),
            reached_bps=Decimal(0),
            ticks_crossed=0,
            reason="the pool has no active liquidity, so its price cannot be moved",
        )

    factor = (BPS + bps) / BPS if upward else (BPS - bps) / BPS
    target_price = start_price * factor
    if target_price <= 0:
        return DepthQuote(
            reachable=False,
            target_bps=bps,
            amount0=Decimal(0),
            amount1=Decimal(0),
            reached_bps=Decimal(0),
            ticks_crossed=0,
            reason="the requested move takes the price to or below zero",
        )

    boundaries = _boundaries(state, upward=upward)

    liquidity = state.active_liquidity
    current_sqrt = sqrt_price(start_price)
    target_sqrt = sqrt_price(target_price)
    amount0 = Decimal(0)
    amount1 = Decimal(0)
    crossed = 0

    for tick in boundaries:
        boundary_sqrt = sqrt_price(price_from_tick(tick))
        # Stop at the target when it falls inside this range.
        segment_end = (
            target_sqrt
            if (upward and target_sqrt <= boundary_sqrt)
            or (not upward and target_sqrt >= boundary_sqrt)
            else boundary_sqrt
        )

        amount0 += amount0_delta(current_sqrt, segment_end, liquidity)
        amount1 += amount1_delta(current_sqrt, segment_end, liquidity)
        current_sqrt = segment_end

        if current_sqrt == target_sqrt:
            return DepthQuote(
                reachable=True,
                target_bps=bps,
                amount0=amount0,
                amount1=amount1,
                reached_bps=bps,
                ticks_crossed=crossed,
            )

        net = state.tick_liquidity_net.get(tick, Decimal(0))
        liquidity = liquidity + net if upward else liquidity - net
        crossed += 1
        if liquidity <= 0:
            # No liquidity beyond this tick that we know of. Consuming what
            # exists is not the same as reaching the target.
            return _unreachable(bps, amount0, amount1, current_sqrt, start_price, crossed)

    # The target lies beyond every initialized tick we know about.
    return _unreachable(bps, amount0, amount1, current_sqrt, start_price, crossed)


def _boundaries(state: PoolState, *, upward: bool) -> list[int]:
    """Initialized ticks between spot and the edge, in traversal order."""
    ticks = state.initialized_ticks
    if upward:
        return [t for t in ticks if t > state.current_tick]
    return [t for t in reversed(ticks) if t <= state.current_tick]


def _unreachable(
    bps: Decimal,
    amount0: Decimal,
    amount1: Decimal,
    reached_sqrt: Decimal,
    start_price: Decimal,
    crossed: int,
) -> DepthQuote:
    reached = reached_sqrt * reached_sqrt
    moved = abs(reached - start_price) / start_price * BPS
    return DepthQuote(
        reachable=False,
        target_bps=bps,
        amount0=amount0,
        amount1=amount1,
        reached_bps=moved,
        ticks_crossed=crossed,
        reason=(
            f"known liquidity is exhausted after {moved:.2f} bps; the amounts "
            "describe reaching that point, not the target"
        ),
    )


#: How far the two sides may differ in cost before a band is called
#: asymmetric. Even a constant-liquidity pool is slightly lopsided -- moving
#: +50 bps and -50 bps are not mirror images in square-root price space, and
#: the gap is about half a percent -- so a zero tolerance would report every
#: pool as asymmetric and the signal would be worthless.
DEFAULT_ASYMMETRY_TOLERANCE = Decimal("0.02")


@dataclass(frozen=True)
class DepthCurve:
    """PRD section 18.7.1's +/-10/25/50/100 bps, both directions."""

    up: dict[str, DepthQuote]
    down: dict[str, DepthQuote]
    #: Spot price, to express both sides' cost in one token.
    price: Decimal
    tolerance: Decimal = DEFAULT_ASYMMETRY_TOLERANCE

    def cost_in_token1(self, quote: DepthQuote, *, upward: bool) -> Decimal:
        """What the move costs, always in token1.

        Going up spends token1; going down spends token0. Comparing those two
        numbers directly would be comparing different currencies -- which the
        first version of this did, and it reported every pool as asymmetric.
        """
        return quote.amount1 if upward else quote.amount0 * self.price

    @property
    def asymmetric_at(self) -> list[str]:
        """Bands where the two sides differ meaningfully.

        The asymmetry is the finding: concentrated liquidity is rarely
        symmetric, and a curve reporting one side would hide which way the pool
        is thin.
        """
        differing = []
        for band, up in self.up.items():
            down = self.down.get(band)
            if down is None:
                continue
            if up.reachable != down.reachable:
                differing.append(band)
                continue
            if not up.reachable:
                continue
            up_cost = self.cost_in_token1(up, upward=True)
            down_cost = self.cost_in_token1(down, upward=False)
            reference = max(up_cost, down_cost)
            if reference == 0:
                continue
            if abs(up_cost - down_cost) / reference > self.tolerance:
                differing.append(band)
        return differing


#: Section 18.7.1's bands, verbatim.
DEFAULT_BANDS: tuple[int, ...] = (10, 25, 50, 100)


def depth_curve(
    state: PoolState,
    *,
    bands: tuple[int, ...] = DEFAULT_BANDS,
    tolerance: Decimal = DEFAULT_ASYMMETRY_TOLERANCE,
) -> DepthCurve:
    return DepthCurve(
        up={f"{b}bps": depth_to_bps(state, bps=Decimal(b), upward=True) for b in bands},
        down={f"{b}bps": depth_to_bps(state, bps=Decimal(b), upward=False) for b in bands},
        price=price_from_sqrt_x96(state.sqrt_price_x96),
        tolerance=tolerance,
    )
