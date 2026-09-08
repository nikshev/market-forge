"""Uniswap v3 pool state, rebuilt from events (PRD section 18.7).

# @trace: REQ-WP-015

    previous pool state + ordered block/log events -> new pool state

The ordering is the rule ADR-035 is about, and it is not a detail: a block's
logs share its timestamp, so a timestamp sort applies a swap before the mint
that supplied its liquidity. The resulting tick map is plausible, the active
liquidity is plausible, and the depth curve computed from them is not the
pool's.

Section 18.7.1's tick structure is sparse -- `tick -> liquidity_net` -- because
a pool has 1.7 million possible ticks and a handful of initialized ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.dex.events import (
    Collect,
    LiquidityChange,
    PoolEvent,
    PoolEventKind,
    Swap,
)


class DuplicateLog(ValueError):
    """Two events share a block, transaction index and log index.

    That triple is a chain's unique identifier for a log, so a repeat is the
    same log ingested twice -- from two providers, or a backfill overlapping
    live ingestion. Deduplicating silently would hide the ingestion bug and
    double a mint (ADR-035).
    """


class NegativeLiquidity(ValueError):
    """A burn exceeded the liquidity at a tick.

    Impossible on-chain, so seeing it means the event sequence is incomplete --
    which is worth stopping for rather than clamping to zero and carrying on
    with a pool that no longer matches.
    """


@dataclass
class PoolState:
    """Current price, active liquidity, and the sparse tick map."""

    address: str
    token0: str
    token1: str
    fee_tier: int
    tick_spacing: int
    current_tick: int = 0
    sqrt_price_x96: int = 0
    active_liquidity: Decimal = Decimal(0)
    #: Section 18.7.1: `tick -> liquidity_net`. Only initialized ticks appear.
    tick_liquidity_net: dict[int, Decimal] = field(default_factory=dict)

    @property
    def initialized_ticks(self) -> list[int]:
        return sorted(t for t, net in self.tick_liquidity_net.items() if net != 0)


def rebuild(state: PoolState, events: list[PoolEvent]) -> PoolState:
    """Apply events in canonical order (ADR-035). Returns a new state.

    Sorting happens here rather than in the caller, so a caller passing events
    in arrival order gets the same answer as one who sorted first -- the same
    reasoning REQ-WP-006's fitter applies to its own window.
    """
    ordered = sorted(events, key=lambda e: e.position.key)

    seen: set[tuple[int, int, int]] = set()
    for event in ordered:
        if event.position.key in seen:
            raise DuplicateLog(
                f"log {event.position.key} appears twice; that triple is unique on "
                "a chain, so this is the same log ingested twice"
            )
        seen.add(event.position.key)

    result = PoolState(
        address=state.address,
        token0=state.token0,
        token1=state.token1,
        fee_tier=state.fee_tier,
        tick_spacing=state.tick_spacing,
        current_tick=state.current_tick,
        sqrt_price_x96=state.sqrt_price_x96,
        active_liquidity=state.active_liquidity,
        tick_liquidity_net=dict(state.tick_liquidity_net),
    )

    for event in ordered:
        if isinstance(event, Swap):
            _apply_swap(result, event)
        elif isinstance(event, LiquidityChange):
            _apply_liquidity(result, event)
        elif isinstance(event, Collect):
            # Section 18.7: LP economics, not liquidity state. Deliberately
            # nothing happens.
            continue
    return result


def _apply_swap(state: PoolState, swap: Swap) -> None:
    """The pool's own state after the trade is authoritative.

    A swap reports where it left the pool, so this is not a recomputation --
    trusting the log over our own arithmetic is what keeps the reconstruction
    anchored to the chain.
    """
    state.current_tick = swap.tick
    state.sqrt_price_x96 = swap.sqrt_price_x96
    state.active_liquidity = swap.liquidity


def _apply_liquidity(state: PoolState, change: LiquidityChange) -> None:
    """A range's liquidity enters at its lower tick and leaves at its upper.

    `liquidity_net` is what a traversal adds when crossing upward, so a mint
    adds at the lower tick and subtracts at the upper. A burn reverses it
    exactly, which is what makes a mint-then-burn pair leave no trace.
    """
    amount = change.signed_amount

    for tick, delta in ((change.tick_lower, amount), (change.tick_upper, -amount)):
        current = state.tick_liquidity_net.get(tick, Decimal(0))
        state.tick_liquidity_net[tick] = current + delta

    if change.kind is PoolEventKind.BURN:
        # Gross liquidity in the range cannot go negative; the net map can, and
        # legitimately does. The check is on the range's own contribution.
        if _range_liquidity(state, change) < 0:
            raise NegativeLiquidity(
                f"burning {change.amount} from [{change.tick_lower}, "
                f"{change.tick_upper}] leaves negative liquidity; the event "
                "sequence is incomplete"
            )

    # Section 18.7: only a range spanning the current tick is active.
    if change.tick_lower <= state.current_tick < change.tick_upper:
        state.active_liquidity += amount
        if state.active_liquidity < 0:
            raise NegativeLiquidity(
                f"active liquidity fell to {state.active_liquidity}; the event "
                "sequence is incomplete"
            )


def _range_liquidity(state: PoolState, change: LiquidityChange) -> Decimal:
    """Net liquidity accumulated at the range's lower tick.

    A single number, not a full traversal: what this guard can see is whether
    this range's own bookkeeping went negative, which is the case a stray burn
    produces.
    """
    return state.tick_liquidity_net.get(change.tick_lower, Decimal(0))


@dataclass(frozen=True)
class IntegrityIncident:
    """PRD section 18.7.2's divergence report.

    Names the fields and their two values. It does not carry a corrected state,
    because "never silently patch historical derived rows" means the correction
    is a new observation, not an edit -- the same rule ADR-033 applies to
    reorgs.
    """

    address: str
    mismatches: dict[str, tuple[str, str]]

    @property
    def diverged(self) -> bool:
        return bool(self.mismatches)


def compare_with_contract(
    reconstructed: PoolState,
    *,
    current_tick: int,
    sqrt_price_x96: int,
    active_liquidity: Decimal,
) -> IntegrityIncident:
    """Section 18.7.2's periodic recovery check."""
    mismatches: dict[str, tuple[str, str]] = {}
    for name, ours, theirs in (
        ("current_tick", reconstructed.current_tick, current_tick),
        ("sqrt_price_x96", reconstructed.sqrt_price_x96, sqrt_price_x96),
        ("active_liquidity", reconstructed.active_liquidity, active_liquidity),
    ):
        if ours != theirs:
            mismatches[name] = (str(ours), str(theirs))
    return IntegrityIncident(address=reconstructed.address, mismatches=mismatches)
