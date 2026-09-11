"""Aerodrome v2 prices each pool by its own invariant (REQ-WP-045).

The fixtures are not recordings of a format. They are the deployed contract's
own answers to the question this module computes, read at a pinned block from
two independent RPC endpoints that agreed. PRD §18.25 asks for the quote curve
to match "contract view within tolerance"; integer arithmetic lets this assert
equality instead, and equality catches a class of error a tolerance hides.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex.aerodrome import (
    DidNotConverge,
    PoolShape,
    amount_out,
    invariant,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "aerodrome"


def _pool(name: str) -> dict[str, Any]:
    path = FIXTURES / f"{name}.jsonl"
    assert path.is_file(), f"missing fixture {path}; regenerate with tools.record.aerodrome_capture"
    return json.loads(path.read_text().splitlines()[0])


def _shape(raw: dict[str, Any]) -> PoolShape:
    return PoolShape(
        stable=raw["stable"],
        decimals0=raw["decimals0"],
        decimals1=raw["decimals1"],
        fee_bps=raw["fee_bps"],
    )


@pytest.fixture
def volatile() -> dict[str, Any]:
    return _pool("v2_volatile")


@pytest.fixture
def stable() -> dict[str, Any]:
    return _pool("v2_stable")


# --- the contract is the oracle ------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize("name", ["v2_volatile", "v2_stable"])
def test_every_quote_matches_the_pool_s_own_answer_exactly(name: str) -> None:
    """§18.25's "matches contract view", asserted as equality.

    Every intermediate in `Pool.sol` is uint256, so a faithful port agrees bit
    for bit. A tolerance here would pass a port that rounded in the wrong
    direction at every step and drifted with size -- which is exactly the error
    a depth curve would carry and nobody would see.
    """
    raw = _pool(name)
    shape = _shape(raw)

    for quote in raw["quotes"]:
        assert amount_out(
            amount_in=int(quote["amount_in"]),
            token_in_is_token0=True,
            reserve0=int(raw["reserve0"]),
            reserve1=int(raw["reserve1"]),
            shape=shape,
        ) == int(quote["amount_out"])


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize("name", ["v2_volatile", "v2_stable"])
def test_the_quotes_span_orders_of_magnitude(name: str) -> None:
    """A port can be right at one size and wrong at another -- the stable
    curve's error grows with the trade. Four sizes across four decades is what
    makes the test above mean something."""
    amounts = [int(q["amount_in"]) for q in _pool(name)["quotes"]]

    assert len(amounts) >= 4
    assert max(amounts) >= min(amounts) * 1000


# --- the two curves are two curves ---------------------------------------------


@pytest.mark.trace("REQ-WP-045")
def test_the_invariants_disagree_on_the_same_reserves(stable: dict[str, Any]) -> None:
    """The assertion that stops a test passing while one curve is used for both.

    Pricing a stable pool as constant product gives a plausible, wrong number,
    and nothing downstream shows a symptom. So the difference is asserted
    directly rather than left to be implied by the quote tests.
    """
    shape = _shape(stable)
    as_volatile = PoolShape(
        stable=False,
        decimals0=shape.decimals0,
        decimals1=shape.decimals1,
        fee_bps=shape.fee_bps,
    )
    reserve0, reserve1 = int(stable["reserve0"]), int(stable["reserve1"])
    amount_in = int(stable["quotes"][-1]["amount_in"])

    correct = amount_out(
        amount_in=amount_in,
        token_in_is_token0=True,
        reserve0=reserve0,
        reserve1=reserve1,
        shape=shape,
    )
    wrong = amount_out(
        amount_in=amount_in,
        token_in_is_token0=True,
        reserve0=reserve0,
        reserve1=reserve1,
        shape=as_volatile,
    )

    assert correct != wrong
    assert invariant(reserve0, reserve1, shape) != invariant(reserve0, reserve1, as_volatile)


@pytest.mark.trace("REQ-WP-045")
def test_a_volatile_pool_conserves_the_product(volatile: dict[str, Any]) -> None:
    reserve0, reserve1 = int(volatile["reserve0"]), int(volatile["reserve1"])

    assert invariant(reserve0, reserve1, _shape(volatile)) == reserve0 * reserve1


# --- the fee comes out first ---------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
def test_the_fee_is_taken_before_the_invariant(volatile: dict[str, Any]) -> None:
    """`getAmountOut` subtracts the fee from the input and then swaps. Taking it
    from the output instead prices a trade the pool never offered, and on a
    curve it is a different number rather than the same one scaled."""
    raw = volatile
    shape = _shape(raw)
    free = PoolShape(
        stable=shape.stable,
        decimals0=shape.decimals0,
        decimals1=shape.decimals1,
        fee_bps=0,
    )
    amount_in = int(raw["quotes"][-1]["amount_in"])
    reserve0, reserve1 = int(raw["reserve0"]), int(raw["reserve1"])

    charged = amount_out(
        amount_in=amount_in,
        token_in_is_token0=True,
        reserve0=reserve0,
        reserve1=reserve1,
        shape=shape,
    )
    uncharged = amount_out(
        amount_in=amount_in,
        token_in_is_token0=True,
        reserve0=reserve0,
        reserve1=reserve1,
        shape=free,
    )
    after_the_fact = uncharged - (uncharged * shape.fee_bps) // 10_000

    assert charged < uncharged
    assert charged != after_the_fact


# --- direction and refusals ----------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize("name", ["v2_volatile", "v2_stable"])
def test_the_two_directions_are_different_quotes(name: str) -> None:
    """Token order is not a formality: a pool with unequal reserves prices the
    two directions differently, and a quote that ignored direction would be
    right in one of them by accident."""
    raw = _pool(name)
    shape = _shape(raw)
    amount_in = int(raw["quotes"][0]["amount_in"])

    forward = amount_out(
        amount_in=amount_in,
        token_in_is_token0=True,
        reserve0=int(raw["reserve0"]),
        reserve1=int(raw["reserve1"]),
        shape=shape,
    )
    backward = amount_out(
        amount_in=amount_in,
        token_in_is_token0=False,
        reserve0=int(raw["reserve0"]),
        reserve1=int(raw["reserve1"]),
        shape=shape,
    )

    assert forward != backward


@pytest.mark.trace("REQ-WP-045")
def test_a_swap_of_nothing_is_refused(volatile: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="nothing"):
        amount_out(
            amount_in=0,
            token_in_is_token0=True,
            reserve0=int(volatile["reserve0"]),
            reserve1=int(volatile["reserve1"]),
            shape=_shape(volatile),
        )


@pytest.mark.trace("REQ-WP-045")
def test_a_pool_with_an_empty_side_cannot_quote(volatile: dict[str, Any]) -> None:
    """Refused rather than returning zero. Zero is a quote, and a quote of zero
    from an empty pool reads as "no liquidity at this price" rather than "this
    pool is not a pool"."""
    with pytest.raises(ValueError, match="empty side"):
        amount_out(
            amount_in=1000,
            token_in_is_token0=True,
            reserve0=0,
            reserve1=int(volatile["reserve1"]),
            shape=_shape(volatile),
        )


#: Stable pools whose reserves and trade size reach the iteration's edges.
#: Found by searching the input space, because the two recorded pools converge
#: cleanly and never touch these paths -- and the contract carries the branches
#: precisely because real pools sometimes do. Reserves are small relative to the
#: trade, which is what a nearly-drained pool looks like.
SETTLES_ON_THE_LATTICE = [
    # (reserve0, reserve1, amount_in, decimals0, decimals1, expected_out)
    (62_632_598_597, 557_957_931_388, 922_121_677, 6, 18, 23_865_990_001),
    (490_871_645_057, 740_882_240_092, 73_778_518_209, 18, 6, 33_693_336_889),
]

#: A stable pool where Newton's method does not settle inside the contract's own
#: budget of 255 steps.
NEVER_SETTLES = (714_660_326_134, 77_516_800_952, 295_585_122_341, 18, 6)


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize(
    ("reserve0", "reserve1", "amount_in", "decimals0", "decimals1", "expected"),
    SETTLES_ON_THE_LATTICE,
)
def test_the_iteration_terminates_on_the_integer_lattice(
    reserve0: int, reserve1: int, amount_in: int, decimals0: int, decimals1: int, expected: int
) -> None:
    """The `dy == 0` branches, which look like defensive noise and are not.

    On integers Newton's step can round to zero while the invariant is still
    off, and without those branches the search stalls at a wrong `y` or
    oscillates by one wei until the budget runs out. The two recorded pools
    never reach this, so the inputs were found by searching.
    """
    shape = PoolShape(stable=True, decimals0=decimals0, decimals1=decimals1, fee_bps=30)

    assert (
        amount_out(
            amount_in=amount_in,
            token_in_is_token0=True,
            reserve0=reserve0,
            reserve1=reserve1,
            shape=shape,
        )
        == expected
    )


@pytest.mark.trace("REQ-WP-045")
def test_the_iteration_refuses_rather_than_approximating() -> None:
    """The contract reverts when Newton's method does not settle in 255 steps,
    and so does this. Returning the last estimate would hand back a number that
    looks like a quote and is not one -- and it would be the quote a caller
    acted on, because nothing about it says it did not converge."""
    reserve0, reserve1, amount_in, decimals0, decimals1 = NEVER_SETTLES
    shape = PoolShape(stable=True, decimals0=decimals0, decimals1=decimals1, fee_bps=30)

    with pytest.raises(DidNotConverge):
        amount_out(
            amount_in=amount_in,
            token_in_is_token0=True,
            reserve0=reserve0,
            reserve1=reserve1,
            shape=shape,
        )


# --- the fixture is one state --------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize("name", ["v2_volatile", "v2_stable"])
def test_the_fixture_is_pinned_to_one_block(name: str) -> None:
    """Reserves from one block and a quote from another describe an arithmetic
    that never existed, and the test would be measuring the gap between two
    states rather than the adapter."""
    raw = _pool(name)

    assert isinstance(raw["block"], int)
    assert raw["block"] > 0
    assert raw["pool"].startswith("0x")
