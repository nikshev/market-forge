"""Aerodrome v2: two curves, and the pool says which (PRD section 18.10).

# @trace: REQ-WP-045

Section 18.10 states the rule this module exists to keep:

    Depth is calculated from the correct pool invariant, not from CL ticks.

A volatile pool is constant product, `x * y = k`. A stable pool is the Solidly
invariant, `k = xy(x² + y²)` on reserves normalised to 1e18 -- which is
`x³y + xy³`, a different curve with a different depth profile at the same
reserves.

**Pricing a stable pool with the constant-product formula gives a plausible
number that is wrong**, and nothing downstream shows a symptom. It is the same
shape as reading a venue's contract sizes as base units: the figure stays
positive, ordered and believable, and every depth curve built on it is wrong by
an amount nobody can reconstruct.

**This is integer arithmetic, deliberately.** The contract's own
`getAmountOut` is `uint256` throughout, with 1e18 normalisation and a
Newton-Raphson search for the output. Ported as integers, this agrees with the
chain **bit for bit** rather than within a tolerance -- and a test that can
assert equality catches a class of error that a tolerance hides.

The source is Aerodrome's published `Pool.sol`: `_k`, `_f`, `_d`, `_get_y` and
`_getAmountOut`. Fees come out of the input *before* the invariant, which is
the contract's order and not an implementation detail -- applying them after
produces a different number.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The contract's normalisation base. Every stable-pool intermediate is scaled
#: to this before the invariant touches it.
WAD = 10**18

#: `getAmountOut` takes the fee in basis points out of the input first.
BPS = 10_000

#: `_get_y`'s iteration budget. The contract reverts past it rather than
#: returning an approximation, and so does this: a quote that did not converge
#: is not a quote.
MAX_ITERATIONS = 255


class DidNotConverge(RuntimeError):
    """Newton's method ran out of iterations.

    The contract reverts here. Returning the last estimate would hand back a
    number that looks like a quote and is not one.
    """


@dataclass(frozen=True)
class PoolShape:
    """What a pool is, read from the chain rather than inferred.

    Solidly-family pools answer `stable()`; a pool that does not is constant
    product. A USDC/USDT pair can be either, so the token names decide nothing.
    """

    stable: bool
    decimals0: int
    decimals1: int
    fee_bps: int


def _scale(decimals: int) -> int:
    """`10 ** decimals`, as the contract stores it.

    A named helper rather than an inline power, so the exponentiation has one
    place to be read and one type.
    """
    return int(10**decimals)


def invariant(x: int, y: int, shape: PoolShape) -> int:
    """`_k` from the contract: the pool's own definition of what it conserves."""
    if not shape.stable:
        return x * y
    _x = (x * WAD) // _scale(shape.decimals0)
    _y = (y * WAD) // _scale(shape.decimals1)
    _a = (_x * _y) // WAD
    _b = ((_x * _x) // WAD) + ((_y * _y) // WAD)
    return (_a * _b) // WAD


def _f(x0: int, y: int) -> int:
    _a = (x0 * y) // WAD
    _b = ((x0 * x0) // WAD) + ((y * y) // WAD)
    return (_a * _b) // WAD


def _d(x0: int, y: int) -> int:
    return (3 * x0 * ((y * y) // WAD)) // WAD + ((((x0 * x0) // WAD) * x0) // WAD)


def _get_y(x0: int, xy: int, y: int, shape: PoolShape) -> int:
    """The contract's Newton-Raphson search for the new reserve.

    Ported step for step, including the `dy == 0` branches. Those look like
    defensive noise and are not: they are what makes the iteration terminate on
    the integer lattice instead of oscillating by one wei forever.
    """
    for _ in range(MAX_ITERATIONS):
        k = _f(x0, y)
        if k < xy:
            dy = ((xy - k) * WAD) // _d(x0, y)
            if dy == 0:
                if k == xy:
                    return y
                if invariant(x0, y + 1, shape) > xy:
                    return y + 1
                dy = 1
            y = y + dy
        else:
            dy = ((k - xy) * WAD) // _d(x0, y)
            if dy == 0:
                if k == xy or _f(x0, y - 1) < xy:
                    return y
                dy = 1
            y = y - dy
    raise DidNotConverge("the invariant search did not settle in 255 steps")


def amount_out(
    *,
    amount_in: int,
    token_in_is_token0: bool,
    reserve0: int,
    reserve1: int,
    shape: PoolShape,
) -> int:
    """What the pool would give, by its own arithmetic.

    The fee comes out first, as `getAmountOut` does it. Taking it afterwards
    would price a trade the pool never offered.
    """
    if amount_in <= 0:
        raise ValueError("a swap of nothing has no output")
    if reserve0 <= 0 or reserve1 <= 0:
        raise ValueError("a pool with an empty side cannot quote")

    amount_in -= (amount_in * shape.fee_bps) // BPS

    if not shape.stable:
        reserve_in, reserve_out = (
            (reserve0, reserve1) if token_in_is_token0 else (reserve1, reserve0)
        )
        return (amount_in * reserve_out) // (reserve_in + amount_in)

    xy = invariant(reserve0, reserve1, shape)
    scaled0 = (reserve0 * WAD) // _scale(shape.decimals0)
    scaled1 = (reserve1 * WAD) // _scale(shape.decimals1)
    reserve_in, reserve_out = (scaled0, scaled1) if token_in_is_token0 else (scaled1, scaled0)
    scaled_in = (amount_in * WAD) // _scale(
        shape.decimals0 if token_in_is_token0 else shape.decimals1
    )
    y = reserve_out - _get_y(scaled_in + reserve_in, xy, reserve_out, shape)
    out_decimals = shape.decimals1 if token_in_is_token0 else shape.decimals0
    return (y * _scale(out_decimals)) // WAD
