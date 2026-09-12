"""PRD §18A.4's directional swap imbalance.

# @trace: REQ-WP-059

    "Since AMM does not expose a traditional bid/ask queue, compute: signed swap
    USD flow; swap count; large swap share; price impact per USD; tick velocity;
    tick crossing count; directional swap imbalance; volume-to-active-liquidity
    ratio."

Eight are named there. **One is built, and the distance is the point.**

`signed swap USD flow` cannot be built honestly today: `notional_usd` is
declared nullable on `DexSwapEvent`, stored as a column by [[REQ-WP-053]], and
set by nothing -- the v3 reducer emits token amounts and no USD price. A feature
computed from it would be absent on every swap, and a pane of it would read "no
readings of this feature" forever, which is indistinguishable from a quiet
market.

`volume-to-active-liquidity ratio` needs §18.12.2's `active_liquidity`, which
lives on a `LiquidityState` nothing reconstructs ([[ADR-067]]).

The signed token amounts *are* produced, so the imbalance is:

    imbalance = sum(amount0) / sum(abs(amount0))

Bounded in [-1, 1] by construction: -1 is every swap taking token0 out of the
pool, +1 every swap putting it in. Denominated in token0 rather than USD, which
is stated in the registration rather than left for a reader to infer from a
number that looks like a fraction either way.

**The entity is the venue_symbol, not the pool.** The features table is keyed by
`(venue, symbol)` and [[REQ-EXP-015]]'s ablation reads DeFi features per
instrument. A second keying nothing consumes would be a promise nothing keeps;
which pool priced the swaps is part of the feature's source, not its key.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from channelflow.domain import DexSwapEvent
from channelflow.features.registry import FeatureSpec, register

FEATURES: tuple[str, ...] = ("dex_swap_imbalance",)


@dataclass(frozen=True)
class SwapImbalance:
    """Which way a window of swaps leaned, and how much went through it."""

    #: Signed sum of `amount0`, from the pool's side.
    signed: Decimal
    #: Sum of `abs(amount0)`. The denominator, and the window's gross flow.
    gross: Decimal
    #: Swaps that carried a direction. A zero-`amount0` swap is not one.
    directional_swaps: int
    #: Every swap in the window, including the ones that moved no token0.
    swaps: int
    window_ns: int
    as_of_ns: int

    @property
    def value(self) -> Decimal | None:
        """The imbalance, or nothing.

        Nothing rather than zero when the gross flow is zero. Zero is the
        reading for a window that was perfectly balanced -- real swaps in both
        directions cancelling -- and a pane drawing a flat line through hours
        with no swaps at all would be claiming balance where there was silence.
        """
        if self.gross == 0:
            return None
        return self.signed / self.gross


def swap_imbalance(
    swaps: Sequence[DexSwapEvent], *, as_of_ns: int, window_ns: int
) -> SwapImbalance:
    """Everything swapped in `(as_of_ns - window_ns, as_of_ns]`.

    Half-open at the floor and closed at `as_of_ns`, as every other windowed
    feature here is, and strictly at or before `as_of_ns`: Constitution
    Principle I, and the reason this can be computed on a historical bar at all.
    """
    if window_ns <= 0:
        raise ValueError(f"a window of {window_ns}ns spans nothing")
    floor = as_of_ns - window_ns
    inside = [swap for swap in swaps if floor < swap.meta.event_time_ns <= as_of_ns]
    # A swap that moved no token0 was measured on chain 999 ([[REQ-WP-058]]):
    # two of eighty-three captured swaps report a zero amount on one side. It
    # has no direction, so it enters neither sum -- but it is still a swap, and
    # the count says so.
    directional = [swap for swap in inside if swap.amount0 != 0]
    return SwapImbalance(
        signed=sum((swap.amount0 for swap in directional), Decimal(0)),
        gross=sum((abs(swap.amount0) for swap in directional), Decimal(0)),
        directional_swaps=len(directional),
        swaps=len(inside),
        window_ns=window_ns,
        as_of_ns=as_of_ns,
    )


def _register_all() -> None:
    register(
        FeatureSpec(
            name="dex_swap_imbalance",
            version=1,
            family="defi",
            description=(
                "Which way a window of AMM swaps leaned, normalized by the gross "
                "token0 flow through the pool."
            ),
            formula="sum(amount0) / sum(abs(amount0)) over swaps in (t - window, t]",
            unit="normalized [-1, 1]",
            source_events=("dex_swap",),
            lookback="the configured window",
            cadence="per swap",
            # A swap is known when its log is, and section 18.19's availability
            # gap belongs to the chain record rather than to this arithmetic.
            availability_lag_ms=0,
            null_policy=(
                "absent when no swap in the window moved token0; zero is the "
                "reading for a balanced window, not for an empty one"
            ),
            clipping="none; bounded in [-1, 1] by construction",
            normalization="divided by the window's gross token0 flow",
            point_in_time_safe=True,
            test_fixture="tests/unit/features/test_dex.py",
        )
    )


_register_all()
