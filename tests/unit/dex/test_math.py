"""PRD section 18.7's price representations (REQ-WP-015)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dex import (
    MAX_TICK,
    Q96,
    human_price,
    price_from_sqrt_x96,
    price_from_tick,
    sqrt_x96_from_price,
    tick_from_price,
)


@pytest.mark.trace("REQ-WP-015")
def test_sqrt_price_x96_is_the_square_of_the_fixed_point_value() -> None:
    """SC-001, FR-001. `(sqrtPriceX96 / 2^96)^2`."""
    encoded = int(Decimal(2).sqrt() * Q96)

    assert price_from_sqrt_x96(encoded) == pytest.approx(Decimal(2), abs=Decimal("1e-20"))


@pytest.mark.trace("REQ-WP-015")
def test_a_price_round_trips_through_the_fixed_point_encoding() -> None:
    """FR-001. The pool stores a truncated integer, so the round trip is close
    rather than exact -- but far closer than any tick's width."""
    for price in ("1", "3000", "0.0004"):
        encoded = sqrt_x96_from_price(Decimal(price))
        assert price_from_sqrt_x96(encoded) == pytest.approx(Decimal(price), rel=Decimal("1e-25"))


@pytest.mark.trace("REQ-WP-015")
def test_tick_zero_is_price_one() -> None:
    """SC-001, FR-002. `1.0001^0`, and the one value that pins the base."""
    assert price_from_tick(0) == pytest.approx(Decimal(1), abs=Decimal("1e-30"))


@pytest.mark.trace("REQ-WP-015")
def test_one_tick_is_one_basis_point() -> None:
    """FR-002. `1.0001` is the tick base, so a single tick is a bp -- which is
    what makes PRD section 18.7.1's bands roughly tick counts."""
    assert price_from_tick(1) == pytest.approx(Decimal("1.0001"), abs=Decimal("1e-20"))


@pytest.mark.trace("REQ-WP-015")
@pytest.mark.parametrize("tick", [-887000, -100000, -1, 0, 1, 100000, 887000])
def test_a_tick_round_trips_through_price(tick: int) -> None:
    """SC-001, FR-003.

    Exercised at the extremes as well as the middle: `1.0001^887000` is about
    10^38, and a naive float implementation loses the round trip long before
    that.
    """
    assert tick_from_price(price_from_tick(tick)) == tick


@pytest.mark.trace("REQ-WP-015")
def test_tick_from_price_floors_rather_than_rounds() -> None:
    """FR-002. The current tick is the one the price sits *in*; rounding would
    put a price at the bottom of a tick into the tick below it."""
    just_above = price_from_tick(100) * Decimal("1.00005")

    assert tick_from_price(just_above) == 100


@pytest.mark.trace("REQ-WP-015")
def test_a_tick_outside_the_pools_bounds_is_refused() -> None:
    """FR-002. The contract's own limits."""
    with pytest.raises(ValueError, match="bounds"):
        price_from_tick(MAX_TICK + 1)


@pytest.mark.trace("REQ-WP-015")
def test_decimals_are_applied_to_the_human_price() -> None:
    """SC-001, FR-004.

    A WETH/USDC pool: token0 has 18 decimals, token1 has 6. One WETH is 3,000
    USDC, so in raw units that is 3,000 x 10^6 per 10^18 -- a raw price of
    3 x 10^-9, which is off by 10^12 from the number anyone would quote. A
    depth figure in raw units is a number nobody can sanity-check.
    """
    raw = Decimal("3e-9")

    assert human_price(raw, decimals0=18, decimals1=6) == pytest.approx(
        Decimal("3000"), rel=Decimal("1e-20")
    )


@pytest.mark.trace("REQ-WP-015")
def test_a_non_positive_price_is_refused() -> None:
    """Nothing downstream has a sensible answer for it, and `ln(0)` is not an
    error a caller would recognise."""
    with pytest.raises(ValueError):
        tick_from_price(Decimal(0))
    with pytest.raises(ValueError):
        sqrt_x96_from_price(Decimal("-1"))
