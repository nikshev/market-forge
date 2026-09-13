"""PRD §18.7's reconstruction, run over the rows the canonical plane holds.

# @trace: REQ-WP-062

[[REQ-WP-053]] stores swaps and liquidity changes; [[REQ-WP-060]] rebuilds a
state from events and grades it. Nothing joined the two, so `dex_state` was a
table with no producer -- the same shape [[REQ-PIPE-001]] closed for the other
seven, closed the same way: a replay over recorded input rather than a daemon.

**The canonical order comes from the row, not from the clock.** §18.7 forbids
sorting on timestamp and names `(block_number, transaction_index, log_index)`.
Both tables now carry the middle field, which they did not until this
requirement -- measured first: over 1,392 real logs in 803 blocks, 305 of them
holding more than one transaction against the pool, ordering by the triple and
ordering by `(block, log_index)` agreed everywhere, so adding the column moves
nothing that already exists.

**A liquidity row states the same fact twice.** It carries a signed
`liquidity_delta` and an `event_type`, and they can disagree. The tick map is
built from the sign, so a row whose type says `burn` over a positive delta is
refused rather than resolved: either half taken alone produces a map that is
plausible and not the pool's.

**A replay that saw no swap has no price.** `sqrt_price_x96` stays zero, which
reads as a price of zero rather than as an absence, and `active_liquidity` stays
zero, which makes the tick-map invariant compare two numbers that mean nothing.
A swap is what anchors a reconstruction to the chain, so a window without one is
refused.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from channelflow.dex.events import (
    Collect,
    LiquidityChange,
    PoolEvent,
    PoolEventKind,
    Position,
    Swap,
)
from channelflow.dex.math import price_from_sqrt_x96
from channelflow.dex.pool import PoolState, rebuild
from channelflow.dex.reconstruction import (
    Provenance,
    Reconciliation,
    ReconstructionQuality,
    quality,
)
from channelflow.tables import dex_state

#: `event_type` values that move liquidity, and the sign each one requires.
#: `modify` is §18.8's v4 `ModifyLiquidity`, which has no counterpart in
#: [[REQ-WP-015]]'s `PoolEventKind`: its effect on the tick map is exactly its
#: signed delta, so it maps by sign, and that is stated here rather than left to
#: whoever reads the enum.
_REQUIRED_SIGN = {"mint": 1, "burn": -1}


class ContradictoryRow(ValueError):
    """A liquidity row whose `event_type` disagrees with its own sign."""


class NothingToReplay(ValueError):
    """No rows for this pool in this range.

    Refused rather than written as an empty state: a `dex_state` row saying a
    pool has no liquidity is a claim about the pool, and this is a fact about
    the query.
    """


class NotAnchored(ValueError):
    """The replay saw no swap, so the state has no price to be anchored to."""


@dataclass(frozen=True)
class PoolIdentity:
    """What a reconstruction needs that the event rows do not carry."""

    chain_id: int
    pool: str
    venue: str
    protocol: str
    token0: str
    token1: str
    fee_tier: int
    tick_spacing: int


def _position(row: dict[str, Any]) -> Position:
    return Position(
        block_number=int(row["block_number"]),
        transaction_index=int(row["transaction_index"]),
        log_index=int(row["log_index"]),
    )


def swap_event(row: dict[str, Any]) -> Swap:
    """One `dex_swaps` row as the event §18.7 applies."""
    return Swap(
        position=_position(row),
        amount0=Decimal(str(row["amount0"])),
        amount1=Decimal(str(row["amount1"])),
        sqrt_price_x96=int(str(row["sqrt_price_x96"])),
        liquidity=Decimal(str(row["liquidity"])),
        tick=int(row["tick"]),
    )


def liquidity_event(row: dict[str, Any]) -> PoolEvent:
    """One `dex_liquidity` row, refusing a row that contradicts itself."""
    event_type = str(row["event_type"])
    delta = int(str(row["liquidity_delta"]))

    if event_type == "collect":
        # §18.7: LP economics, not liquidity state. Carried so the sequence is
        # complete and deliberately inert.
        return Collect(
            position=_position(row),
            amount0=Decimal(str(row["amount0"] or 0)),
            amount1=Decimal(str(row["amount1"] or 0)),
        )

    if delta == 0:
        # **A `Burn` of zero is real and common**: it is how a position is poked
        # to settle fees before collecting, and four of the fifteen mint/burn
        # logs in the fixture are exactly that.
        #
        # It moves no liquidity, so it is applied as a change of nothing -- and
        # specifically not as a burn. [[REQ-WP-015]]'s burn guard refuses a
        # sequence whose range went negative, which is what a partial replay
        # looks like when the matching mint is older than the window. Refusing
        # the whole replay over a row that moved nothing would be refusing for a
        # fact about the window, reported against this row.
        return LiquidityChange(
            position=_position(row),
            tick_lower=int(row["tick_lower"]),
            tick_upper=int(row["tick_upper"]),
            amount=Decimal(0),
            kind=PoolEventKind.MINT,
        )

    required = _REQUIRED_SIGN.get(event_type)
    if required is not None and (delta > 0) != (required > 0):
        raise ContradictoryRow(
            f"{event_type} at block {row['block_number']} log {row['log_index']} carries "
            f"liquidity_delta {delta}; the type and the sign state the same fact and "
            "disagree, and the tick map is built from the sign"
        )

    return LiquidityChange(
        position=_position(row),
        tick_lower=int(row["tick_lower"]),
        tick_upper=int(row["tick_upper"]),
        amount=Decimal(abs(delta)),
        kind=PoolEventKind.MINT if delta > 0 else PoolEventKind.BURN,
    )


def events_for(
    *, swaps: Sequence[dict[str, Any]], liquidity: Sequence[dict[str, Any]]
) -> list[PoolEvent]:
    """Both tables' rows as one sequence.

    Unsorted: `rebuild` sorts on §18.7's key itself, so a caller who passes rows
    in arrival order gets the same answer as one who sorted first.
    """
    return [*(swap_event(row) for row in swaps), *(liquidity_event(row) for row in liquidity)]


@dataclass(frozen=True)
class Materialized:
    """A rebuilt state, its grade, and the row that records both."""

    state: PoolState
    quality: ReconstructionQuality
    reference_price: Decimal
    row: dict[str, object]


def materialize(
    *,
    identity: PoolIdentity,
    swaps: Sequence[dict[str, Any]],
    liquidity: Sequence[dict[str, Any]],
    provenance: Provenance,
    state_time_ns: int,
    initial: PoolState | None = None,
    reconciliation: Reconciliation | None = None,
) -> Materialized:
    """Replay a pool's stored rows into one `dex_state` row."""
    events = events_for(swaps=swaps, liquidity=liquidity)
    if not events:
        raise NothingToReplay(
            f"no swap or liquidity rows for {identity.pool} in blocks "
            f"{provenance.from_block}-{provenance.to_block}; an empty state would be a "
            "claim about the pool rather than about the query"
        )

    state = rebuild(
        initial
        or PoolState(
            address=identity.pool,
            token0=identity.token0,
            token1=identity.token1,
            fee_tier=identity.fee_tier,
            tick_spacing=identity.tick_spacing,
        ),
        events,
    )

    if state.sqrt_price_x96 <= 0:
        raise NotAnchored(
            f"{identity.pool} was replayed over {len(events)} event(s) and none was a swap, "
            "so the state carries no price; a reference price of zero would read as a "
            "price rather than as an absence"
        )

    verdict = quality(state, provenance=provenance, reconciliation=reconciliation)
    price = price_from_sqrt_x96(state.sqrt_price_x96)
    return Materialized(
        state=state,
        quality=verdict,
        reference_price=price,
        row=dex_state.to_row(
            state,
            chain_id=identity.chain_id,
            venue=identity.venue,
            protocol=identity.protocol,
            reference_price=price,
            state_time_ns=state_time_ns,
            quality=verdict,
            provenance=provenance,
        ),
    )
