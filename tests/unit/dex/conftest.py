"""A pool whose arithmetic can be checked by hand (REQ-WP-015)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dex import (
    LiquidityChange,
    PoolEventKind,
    PoolState,
    Position,
    Swap,
    sqrt_x96_from_price,
)


def position(block: int, tx: int = 0, log: int = 0) -> Position:
    return Position(block_number=block, transaction_index=tx, log_index=log)


def mint(
    *, block: int, lower: int, upper: int, amount: str, tx: int = 0, log: int = 0
) -> LiquidityChange:
    return LiquidityChange(
        position=position(block, tx, log),
        tick_lower=lower,
        tick_upper=upper,
        amount=Decimal(amount),
        kind=PoolEventKind.MINT,
    )


def burn(
    *, block: int, lower: int, upper: int, amount: str, tx: int = 0, log: int = 0
) -> LiquidityChange:
    return LiquidityChange(
        position=position(block, tx, log),
        tick_lower=lower,
        tick_upper=upper,
        amount=Decimal(amount),
        kind=PoolEventKind.BURN,
    )


def swap(*, block: int, price: str, tick: int, liquidity: str, tx: int = 0, log: int = 0) -> Swap:
    return Swap(
        position=position(block, tx, log),
        amount0=Decimal("-1"),
        amount1=Decimal("1"),
        sqrt_price_x96=sqrt_x96_from_price(Decimal(price)),
        liquidity=Decimal(liquidity),
        tick=tick,
    )


def pool(**overrides: object) -> PoolState:
    """A pool at price 1.0 (tick 0), so hand arithmetic stays legible."""
    fields: dict[str, object] = {
        "address": "0xPOOL",
        "token0": "0xTOKEN0",
        "token1": "0xTOKEN1",
        "fee_tier": 3000,
        "tick_spacing": 60,
        "current_tick": 0,
        "sqrt_price_x96": sqrt_x96_from_price(Decimal(1)),
        "active_liquidity": Decimal("1000000"),
    }
    fields.update(overrides)
    return PoolState(**fields)  # type: ignore[arg-type]


@pytest.fixture
def deep_pool() -> PoolState:
    """Liquidity spanning far past 100 bps in both directions.

    +/-100 bps is roughly +/-100 ticks, so boundaries at +/-5000 are well
    outside every band and no traversal crosses them.
    """
    state = pool()
    state.tick_liquidity_net = {-5000: Decimal("1000000"), 5000: Decimal("-1000000")}
    return state
