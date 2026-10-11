"""The two DEX features as of a bar's close, from stored swaps and pool readings (REQ-WP-099).

# @trace: REQ-WP-099

Pure, like `context_values` and `liquidation_values`: no table, no clock. The definitions are
[[REQ-WP-059]]'s and [[REQ-WP-063]]'s -- `swap_imbalance` and `active_liquidity_at` -- and this adds
the three things a close needs that a library function does not know:

**What was knowable at the close.** A swap counts if its block time is at or before the close *and*
we had stored it by then. The block's time alone is not availability ([[REQ-WP-014]]; PRD §18.19): a
swap from the second before a close that the collector stored after it is not in that close.

**Quiet is a reading only where the collector was listening.** Few swaps in five minutes is a fact
about the market only if the collector asked for every minute of the five. A window is evaluated
only if **every** registered pool has a reading in every minute of it (`liquidation_values.covered`,
the same rule); otherwise there is no imbalance for that close. A covered window with nothing in it
has none either: zero would read "balanced", which is a fact about a busy window.

**A liquidity figure is current for three polls.** `active_liquidity_at` takes the newest usable
reading however old; a pool the collector stopped reading would keep its last figure for ever. Past
three polls the figure is not the pool's liquidity now, and there is none.

The liquidity shown is **one pool's** (`liquidity_pool`): it is in the pool's own units and is not
comparable across pools ([[REQ-WP-063]]), so adding two would be a number that means nothing.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from channelflow.features.dex import LiquidityReading, active_liquidity_at, swap_imbalance
from channelflow.features.liquidation_values import covered

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS

DEX_FEATURES: tuple[str, ...] = ("dex_swap_imbalance", "dex_active_liquidity")

#: The trailing window of the imbalance: the liquidation features' five minutes, so the panes of one
#: row read over the same span.
WINDOW_NS = 5 * MINUTE_NS

#: Three polls of the DEX collector (30 s each; `hyperevm_collect.POLL_INTERVAL_S`, which a test
# pins : this to): one missed poll is tolerated, three are not.
LIQUIDITY_STALENESS_NS = 3 * 30 * SECOND_NS


@dataclass(frozen=True)
class _Moment:
    event_time_ns: int


@dataclass(frozen=True)
class StoredSwap:
    """A swap as the table holds it: when it happened, when it was stored, and its token0
    movement."""

    pool: str
    event_time_ns: int
    ingest_time_ns: int
    amount0: Decimal

    @property
    def meta(self) -> _Moment:
        return _Moment(self.event_time_ns)


class DexSeries:
    """The stored swaps and readings of one series, indexed once so a close costs a few bisections.

    A backfill evaluates the same series at tens of thousands of closes; filtering the whole history
    at each would be quadratic. `readings` maps each pool to its readings; both inputs are sorted
    here.
    """

    def __init__(
        self,
        swaps: Sequence[StoredSwap],
        readings: Mapping[str, Sequence[LiquidityReading]],
        *,
        pools: Sequence[str],
        liquidity_pool: str,
    ) -> None:
        self._swaps = sorted(swaps, key=lambda s: s.event_time_ns)
        self._swap_times = [s.event_time_ns for s in self._swaps]
        self._pools = tuple(pools)
        self._readings = {
            pool: sorted(readings.get(pool, ()), key=lambda r: r.state_time_ns)
            for pool in {*pools, liquidity_pool}
        }
        self._reading_times = {
            pool: [r.state_time_ns for r in rows] for pool, rows in self._readings.items()
        }
        self._liquidity_pool = liquidity_pool

    def values(self, close_ns: int) -> dict[str, float]:
        """The DEX features at `close_ns`; a feature with nothing honest to say is absent."""
        values: dict[str, float] = {}

        # `covered` looks only at the slots up to the close, so readings after it cannot cover.
        if all(
            covered(self._reading_times[pool], close_ns=close_ns, window_ns=WINDOW_NS)
            for pool in self._pools
        ):
            lo = bisect_right(self._swap_times, close_ns - WINDOW_NS)
            hi = bisect_right(self._swap_times, close_ns)
            known = [s for s in self._swaps[lo:hi] if s.ingest_time_ns <= close_ns]
            imbalance = swap_imbalance(known, as_of_ns=close_ns, window_ns=WINDOW_NS).value
            if imbalance is not None:
                values["dex_swap_imbalance"] = float(imbalance)

        times = self._reading_times[self._liquidity_pool]
        recent = self._readings[self._liquidity_pool][
            bisect_left(times, close_ns - LIQUIDITY_STALENESS_NS) : bisect_right(times, close_ns)
        ]
        liquidity = active_liquidity_at(recent, at_ns=close_ns)
        if liquidity is not None:
            values["dex_active_liquidity"] = liquidity
        return values


def dex_values(
    swaps: Sequence[StoredSwap],
    readings: Mapping[str, Sequence[LiquidityReading]],
    *,
    close_ns: int,
    pools: Sequence[str],
    liquidity_pool: str,
) -> dict[str, float]:
    """One close, without keeping the index: the form a test or a single evaluation wants."""
    return DexSeries(swaps, readings, pools=pools, liquidity_pool=liquidity_pool).values(close_ns)
