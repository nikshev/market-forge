"""Uniswap v3's pool events (PRD section 18.7).

# @trace: REQ-WP-015

`Swap`, `Mint` and `Burn` change liquidity state. `Collect` does not -- section
18.7 is explicit that it is "optional `Collect` for LP economics, not for
liquidity state itself", and decoding it into the tick map would corrupt state
it is not part of.

Every event carries its canonical position: block, transaction index, log
index. Section 18.7 forbids ordering by timestamp, and ADR-035 is why -- a
block's logs all share its timestamp, so a timestamp sort applies a swap before
the mint that supplied its liquidity, and the result is a plausible pool that
is not the one on chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PoolEventKind(StrEnum):
    SWAP = "Swap"
    MINT = "Mint"
    BURN = "Burn"
    #: Decoded and deliberately inert (section 18.7).
    COLLECT = "Collect"


@dataclass(frozen=True)
class Position:
    """Where a log sits in the chain's only total order."""

    block_number: int
    transaction_index: int
    log_index: int

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.block_number, self.transaction_index, self.log_index)


@dataclass(frozen=True)
class Swap:
    """A trade through the pool. Carries the state it left behind."""

    position: Position
    amount0: Decimal
    amount1: Decimal
    sqrt_price_x96: int
    liquidity: Decimal
    tick: int
    kind: PoolEventKind = PoolEventKind.SWAP


@dataclass(frozen=True)
class LiquidityChange:
    """A `Mint` or a `Burn`: liquidity added to or removed from a tick range."""

    position: Position
    tick_lower: int
    tick_upper: int
    amount: Decimal
    kind: PoolEventKind

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.kind is PoolEventKind.MINT else -self.amount


@dataclass(frozen=True)
class Collect:
    """Fees withdrawn. Present so the sequence is complete, and inert."""

    position: Position
    amount0: Decimal
    amount1: Decimal
    kind: PoolEventKind = PoolEventKind.COLLECT


PoolEvent = Swap | LiquidityChange | Collect
