"""PRD section 18.7.1's executable liquidity curve (REQ-WP-015)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dex import (
    DEFAULT_BANDS,
    PoolState,
    depth_curve,
    depth_to_bps,
)
from channelflow.dex.math import amount1_delta, sqrt_price

from .conftest import pool


@pytest.mark.trace("REQ-WP-015")
def test_single_range_depth_matches_the_closed_form(deep_pool: PoolState) -> None:
    """SC-006, FR-012.

    With no tick crossed, the answer is the closed form directly:

        Δy = L * (√P_target - √P_current)

    Computing it two ways is the point: the walk and the formula must agree
    where the walk has nothing to walk.
    """
    quote = depth_to_bps(deep_pool, bps=Decimal(50), upward=True)

    expected = amount1_delta(
        sqrt_price(Decimal(1)),
        sqrt_price(Decimal(1) * Decimal("1.005")),
        deep_pool.active_liquidity,
    )

    assert quote.reachable
    assert quote.ticks_crossed == 0
    assert quote.amount1 == pytest.approx(expected, rel=Decimal("1e-20"))


@pytest.mark.trace("REQ-WP-015")
def test_zero_basis_points_costs_nothing(deep_pool: PoolState) -> None:
    """The spec's fourth edge case: correct, and not a division by zero."""
    quote = depth_to_bps(deep_pool, bps=Decimal(0), upward=True)

    assert quote.reachable
    assert quote.amount0 == Decimal(0)
    assert quote.amount1 == Decimal(0)


@pytest.mark.trace("REQ-WP-015")
def test_depth_rises_with_distance(deep_pool: PoolState) -> None:
    """FR-012. Monotonic, or the curve means nothing."""
    quotes = [depth_to_bps(deep_pool, bps=Decimal(b), upward=True) for b in DEFAULT_BANDS]

    assert all(q.reachable for q in quotes)
    amounts = [q.amount1 for q in quotes]
    assert amounts == sorted(amounts)
    assert len(set(amounts)) == len(amounts)


@pytest.mark.trace("REQ-WP-015")
def test_crossing_a_tick_changes_the_liquidity_used() -> None:
    """SC-007, FR-012.

    Two pools, identical except that one has a liquidity boundary 20 ticks
    above spot -- inside the 50 bps band, which is about 50 ticks. Crossing it
    halves the liquidity, so the same price move costs less token1 beyond the
    boundary and the totals must differ.
    """
    flat = pool()
    flat.tick_liquidity_net = {-5000: Decimal("1000000"), 5000: Decimal("-1000000")}

    stepped = pool()
    stepped.tick_liquidity_net = {
        -5000: Decimal("1000000"),
        20: Decimal("-500000"),
        5000: Decimal("-500000"),
    }

    flat_quote = depth_to_bps(flat, bps=Decimal(50), upward=True)
    stepped_quote = depth_to_bps(stepped, bps=Decimal(50), upward=True)

    assert flat_quote.ticks_crossed == 0
    assert stepped_quote.ticks_crossed == 1
    assert stepped_quote.amount1 < flat_quote.amount1, (
        "beyond the boundary there is half the liquidity, so the same move is cheaper"
    )


@pytest.mark.trace("REQ-WP-015")
def test_a_target_beyond_known_liquidity_is_unreachable() -> None:
    """SC-008, FR-013, ADR-036.

    Returning the notional consumed so far would read as "it costs this much to
    move the price 100 bps" when it actually cost that much to exhaust what we
    know about.
    """
    # A pool whose liquidity ends just above spot. The range opens below the
    # current tick and closes at 30, which is what makes it a pool that could
    # exist: liquidity active at tick 0 has to have been minted at or below it,
    # and a map saying otherwise is an incomplete map rather than a thin pool
    # ([[REQ-WP-060]]).
    thin = pool()
    thin.tick_liquidity_net = {-30: Decimal("1000000"), 30: Decimal("-1000000")}

    quote = depth_to_bps(thin, bps=Decimal(100), upward=True)

    assert not quote.reachable
    assert "exhausted" in quote.reason
    assert quote.reached_bps < Decimal(100)
    assert quote.reached_bps > 0, "it got somewhere before running out"


@pytest.mark.trace("REQ-WP-015")
def test_an_unreachable_quote_still_reports_how_far_it_got() -> None:
    """ADR-036. The partial figures are available on the refusal, so a caller
    who genuinely wants "how far can we get" asks for it rather than receiving
    it by accident."""
    thin = pool()
    thin.tick_liquidity_net = {-30: Decimal("1000000"), 30: Decimal("-1000000")}

    quote = depth_to_bps(thin, bps=Decimal(100), upward=True)

    assert quote.amount1 > 0
    assert quote.ticks_crossed == 1


@pytest.mark.trace("REQ-WP-015")
def test_a_pool_with_no_active_liquidity_cannot_be_moved() -> None:
    """SC-008, FR-013, the spec's fifth edge case: not a cost of zero."""
    empty = pool(active_liquidity=Decimal(0))

    quote = depth_to_bps(empty, bps=Decimal(10), upward=True)

    assert not quote.reachable
    assert "no active liquidity" in quote.reason
    assert quote.amount1 == Decimal(0)


@pytest.mark.trace("REQ-WP-015")
def test_both_directions_are_computed(deep_pool: PoolState) -> None:
    """FR-014. Downward is token0 in, token1 out."""
    up = depth_to_bps(deep_pool, bps=Decimal(50), upward=True)
    down = depth_to_bps(deep_pool, bps=Decimal(50), upward=False)

    assert up.reachable and down.reachable
    assert up.amount0 > 0 and down.amount0 > 0


@pytest.mark.trace("REQ-WP-015")
def test_the_curve_reports_where_the_pool_is_asymmetric() -> None:
    """SC-007, FR-014.

    Concentrated liquidity is rarely symmetric, and a curve reporting one side
    would hide which way the pool is thin. Here liquidity ends 40 ticks above
    spot and continues far below.
    """
    lopsided = pool()
    lopsided.tick_liquidity_net = {-5000: Decimal("1000000"), 40: Decimal("-1000000")}

    curve = depth_curve(lopsided)

    assert curve.up["100bps"].reachable is False
    assert curve.down["100bps"].reachable is True
    assert "100bps" in curve.asymmetric_at


@pytest.mark.trace("REQ-WP-015")
def test_a_symmetric_pool_reports_no_asymmetry(deep_pool: PoolState) -> None:
    """Guard on the guard: a curve that always reported asymmetry would be
    noise, and noise gets muted.

    The first version of `asymmetric_at` compared token1 spent going up against
    token1 *received* going down -- different currencies -- and duly reported
    every band of a symmetric pool as lopsided. Costs are now compared in one
    token, and the tolerance covers the half-percent that square-root price
    space makes unavoidable even at constant liquidity.
    """
    curve = depth_curve(deep_pool)

    assert curve.asymmetric_at == []


@pytest.mark.trace("REQ-WP-015")
def test_a_negative_band_is_refused(deep_pool: PoolState) -> None:
    """Direction is a separate argument; a negative distance would make two
    ways to say the same thing and one of them wrong."""
    with pytest.raises(ValueError, match="negative"):
        depth_to_bps(deep_pool, bps=Decimal(-10), upward=True)


@pytest.mark.trace("REQ-WP-015")
def test_a_pool_with_no_price_is_refused() -> None:
    """An uninitialized pool has no spot to move from.

    It has no liquidity either, so the fixture says so: a pool with a million
    units of active liquidity and no price is not a pool, and it would now be
    refused for the tick map instead ([[REQ-WP-060]]).
    """
    with pytest.raises(ValueError, match="no price"):
        depth_to_bps(
            pool(sqrt_price_x96=0, active_liquidity=Decimal(0)), bps=Decimal(10), upward=True
        )


@pytest.mark.trace("REQ-WP-015")
def test_the_curve_covers_the_bands_the_prd_names(deep_pool: PoolState) -> None:
    """PRD section 18.7.1: "cumulative notional required for +/-10/25/50/100
    bps"."""
    curve = depth_curve(deep_pool)

    assert sorted(curve.up) == sorted(curve.down)
    assert set(curve.up) == {"10bps", "25bps", "50bps", "100bps"}
