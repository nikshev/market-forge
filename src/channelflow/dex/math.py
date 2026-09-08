"""Uniswap v3's three ways of saying "price" (PRD section 18.7).

# @trace: REQ-WP-015

A pool reports `sqrtPriceX96` -- the square root of the price, in Q64.96 fixed
point -- and a tick, where `price = 1.0001^tick`. Both mean token1 per token0
in the pool's raw units, before decimals.

Every number in this adapter is derived from these conversions, and a rounding
error here becomes a wrong depth curve. A depth curve is not obviously wrong
from looking at it, so the arithmetic is `Decimal` at the project's configured
precision (ADR-006) rather than float.
"""

from __future__ import annotations

import math
from decimal import Decimal

#: Q64.96 fixed point: the pool stores sqrt(price) * 2^96.
Q96 = Decimal(2) ** 96
#: The tick base. `price = TICK_BASE ** tick`.
TICK_BASE = Decimal("1.0001")
#: Uniswap v3's tick bounds, from the contract's own limits.
MIN_TICK = -887272
MAX_TICK = 887272


def price_from_sqrt_x96(sqrt_price_x96: int) -> Decimal:
    """`(sqrtPriceX96 / 2^96)^2`, in token1 per token0."""
    root = Decimal(sqrt_price_x96) / Q96
    return root * root


def sqrt_x96_from_price(price: Decimal) -> int:
    """The inverse, truncated to an integer as the pool stores it."""
    if price <= 0:
        raise ValueError("price must be positive")
    return int((price.sqrt() * Q96).to_integral_value())


def price_from_tick(tick: int) -> Decimal:
    """`1.0001^tick`.

    Computed through `exp(tick * ln(1.0001))` in `Decimal`: raising a Decimal
    to a large integer power is exact but grows the intermediate to thousands
    of digits, and the exactness buys nothing a tick's own granularity does not
    already lose.
    """
    if not MIN_TICK <= tick <= MAX_TICK:
        raise ValueError(f"tick {tick} is outside Uniswap v3's bounds")
    return (Decimal(tick) * TICK_BASE.ln()).exp()


def tick_from_price(price: Decimal) -> int:
    """The greatest tick whose price is at or below `price`.

    Floored rather than rounded, matching the pool: the current tick is the one
    the price sits *in*, and rounding would put a price at the bottom of a tick
    into the tick below it.
    """
    if price <= 0:
        raise ValueError("price must be positive")
    raw = price.ln() / TICK_BASE.ln()
    tick = math.floor(raw)
    # `ln` is not exact, so a price sitting exactly on a tick boundary can land
    # a hair below it. Step up when the next tick's price is still at or below
    # the input.
    while tick + 1 <= MAX_TICK and price_from_tick(tick + 1) <= price:
        tick += 1
    while tick > MIN_TICK and price_from_tick(tick) > price:
        tick -= 1
    return tick


def human_price(price: Decimal, *, decimals0: int, decimals1: int) -> Decimal:
    """The pool's raw price adjusted for token decimals.

    A USDC/WETH pool's raw price is off by 10^12 from what anyone would quote,
    and a depth figure in raw units is a number nobody can sanity-check.
    """
    return price * Decimal(10) ** (decimals0 - decimals1)


def amount0_delta(sqrt_a: Decimal, sqrt_b: Decimal, liquidity: Decimal) -> Decimal:
    """Token0 between two square-root prices at constant liquidity.

        Δx = L * (1/√Pa - 1/√Pb)

    Ordered so the result is positive: the caller says which way the price
    moved, and a signed amount here would make every call site remember.
    """
    low, high = (sqrt_a, sqrt_b) if sqrt_a <= sqrt_b else (sqrt_b, sqrt_a)
    if low <= 0:
        raise ValueError("square-root price must be positive")
    return liquidity * (high - low) / (low * high)


def amount1_delta(sqrt_a: Decimal, sqrt_b: Decimal, liquidity: Decimal) -> Decimal:
    """Token1 between two square-root prices at constant liquidity.

    Δy = L * (√Pb - √Pa)
    """
    low, high = (sqrt_a, sqrt_b) if sqrt_a <= sqrt_b else (sqrt_b, sqrt_a)
    return liquidity * (high - low)


def sqrt_price(price: Decimal) -> Decimal:
    if price <= 0:
        raise ValueError("price must be positive")
    return price.sqrt()
