"""PRD sections 16.2 and 16.3 (REQ-WP-013)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.derivatives import (
    PriceOIRegime,
    ZScoreUnavailable,
    basis_bps,
    mark_premium_bps,
    oi_change,
    oi_series,
    oi_to_volume,
    oi_z,
    price_oi_regime,
)

from .conftest import BASE_NS, MINUTE_NS, state


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


@pytest.mark.trace("REQ-WP-013")
def test_base_only_states_are_skipped() -> None:
    """The spec's third edge case: multiplying base units by a price we chose
    would invent a figure the venue did not report."""
    states = [state(at=10, oi_base=500.0), state(at=20, oi_usd=1_000.0)]

    points = oi_series(states, at_ns=at(30))

    assert [p.open_interest_usd for p in points] == [1_000.0]


@pytest.mark.trace("REQ-WP-013")
def test_change_is_measured_from_before_the_window() -> None:
    """FR-005. From the last observation at or before the window's start, not
    the first inside it: a window opening in a gap should compare against what
    was actually known then."""
    states = [
        state(at=0, oi_usd=1_000.0),
        state(at=50, oi_usd=1_500.0),
        state(at=60, oi_usd=1_800.0),
    ]

    change = oi_change(states, at_ns=at(60), window_ns=30 * MINUTE_NS)

    assert change == pytest.approx(800.0), "compared against minute 0, not minute 50"


@pytest.mark.trace("REQ-WP-013")
def test_a_window_with_nothing_before_it_has_no_change() -> None:
    """FR-005. Absent rather than measured from the first observation inside."""
    states = [state(at=50, oi_usd=1_500.0)]

    assert oi_change(states, at_ns=at(60), window_ns=30 * MINUTE_NS) is None


@pytest.mark.trace("REQ-WP-013")
def test_oi_z_refuses_a_short_window() -> None:
    """FR-002, ADR-026."""
    states = [state(at=i, oi_usd=1_000.0 + i) for i in range(5)]

    with pytest.raises(ZScoreUnavailable, match="needs 20"):
        oi_z(states, at_ns=at(100), window=20)


@pytest.mark.trace("REQ-WP-013")
def test_the_ratio_is_absent_on_no_volume() -> None:
    """FR-007, SC-003. Never infinite and never zero: both are values a
    consumer would plot, and one of them means "balanced"."""
    assert oi_to_volume(1_000.0, 0.0) is None
    assert oi_to_volume(1_000.0, 250.0) == pytest.approx(4.0)


@pytest.mark.trace("REQ-WP-013")
@pytest.mark.parametrize(
    ("price_change", "oi_change_usd", "expected"),
    [
        (1.0, 1.0, PriceOIRegime.NEW_RISK_ENTERING),
        (1.0, -1.0, PriceOIRegime.SHORT_COVERING),
        (-1.0, 1.0, PriceOIRegime.NEW_SHORTS),
        (-1.0, -1.0, PriceOIRegime.LONG_LIQUIDATION),
    ],
)
def test_each_quadrant_is_labelled(
    price_change: float, oi_change_usd: float, expected: PriceOIRegime
) -> None:
    """SC-003, FR-006. PRD section 16.2's matrix, all four cells."""
    assert price_oi_regime(price_change=price_change, oi_change_usd=oi_change_usd) is expected


@pytest.mark.trace("REQ-WP-013")
def test_a_flat_leg_is_undetermined() -> None:
    """Not in the PRD, and necessary: a flat leg is in none of the four
    quadrants, and forcing it into one would invent a reading."""
    assert price_oi_regime(price_change=0.0, oi_change_usd=5.0) is PriceOIRegime.UNDETERMINED
    assert price_oi_regime(price_change=5.0, oi_change_usd=0.0) is PriceOIRegime.UNDETERMINED


@pytest.mark.trace("REQ-WP-013")
def test_the_regime_names_keep_the_prds_hedge() -> None:
    """ADR-027. Every label ends in "candidate", which is the PRD hedging its
    own matrix -- and which survives copy-paste into a dashboard where "new
    shorts" alone would read as a fact."""
    for regime in (
        PriceOIRegime.NEW_RISK_ENTERING,
        PriceOIRegime.SHORT_COVERING,
        PriceOIRegime.NEW_SHORTS,
        PriceOIRegime.LONG_LIQUIDATION,
    ):
        assert "candidate" in regime.value


@pytest.mark.trace("REQ-WP-013")
def test_basis_is_relative_to_spot() -> None:
    """SC-004, FR-008. Hand-computed: 112,560 against 112,000 is 50 bps."""
    assert basis_bps(perp_price=Decimal("112560"), spot_price=Decimal("112000")) == pytest.approx(
        50.0
    )


@pytest.mark.trace("REQ-WP-013")
def test_the_mark_premium_is_relative_to_the_index() -> None:
    """SC-004, FR-008. A different denominator from basis, deliberately.

    Hand-computed: -224 against an index of 112,000 is exactly -20 bps. The
    first version of this test divided by the mark instead and expected -20
    from a ratio that gives -19.96 -- which is precisely the error using the
    wrong denominator produces, and small enough to have been waved through.
    """
    assert mark_premium_bps(
        mark_price=Decimal("111776"), index_price=Decimal("112000")
    ) == pytest.approx(-20.0)


@pytest.mark.trace("REQ-WP-013")
def test_a_missing_leg_is_absent_not_zero() -> None:
    """FR-008. Zero basis means perp and spot agree, which is a fact -- and not
    the one being reported when a price is missing."""
    assert basis_bps(perp_price=None, spot_price=Decimal("112000")) is None
    assert basis_bps(perp_price=Decimal("112000"), spot_price=None) is None
    assert mark_premium_bps(mark_price=Decimal("1"), index_price=Decimal("0")) is None
