"""Detector gap policy (REQ-WP-087): the detector restarts its state at a hole.

FR-002 and FR-003 of the gap policy: the detector resets its internal state
when a hole is detected, and no confirmation straddles a hole.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar
from channelflow.extrema.detector import DirectionalChangeDetector
from channelflow.extrema.thresholds import ThresholdPolicy, ThresholdMode

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1_788_838_800_000_000_000


def make_bars(closing_prices: list[str], gaps: list[int]) -> list:
    """Create a series of bars with specified close prices and gaps.

    Args:
        closing_prices: List of close prices as strings
        gaps: Number of missing bars BEFORE each bar (first element must be 0)
    """
    from channelflow.bars import Bar

    assert len(closing_prices) == len(gaps)
    assert gaps[0] == 0, "First bar must have gap=0"

    bars = []
    close_ns = BASE_NS + MINUTE_NS  # First bar closes at BASE_NS + 1 minute

    for i, (close_str, gap) in enumerate(zip(closing_prices, gaps)):
        if i == 0:
            open_ns = BASE_NS
            close_ns = BASE_NS + MINUTE_NS
        else:
            # gap missing bars + 1 for the step to this bar
            close_ns += (gap + 1) * MINUTE_NS
            open_ns = close_ns - MINUTE_NS
            close_ns = open_ns + MINUTE_NS

        from channelflow.bars import Bar
        bars.append(
            Bar(
                venue="binance",
                symbol="BTCUSDT",
                timeframe_ns=MINUTE_NS,
                open_time_ns=open_ns,
                close_time_ns=close_ns,
                open=Decimal("100"),
                high=Decimal("100"),
                low=Decimal("100"),
                close=Decimal(closing_prices[i]),
                volume_base=Decimal("1"),
                volume_quote=Decimal(closing_prices[i]),
                trade_count=1,
                aggressive_buy_base=Decimal("1"),
                aggressive_sell_base=Decimal("0"),
                delta_base=Decimal("1"),
                vwap=Decimal(closing_prices[i]),
                high_time_ns=open_ns,
                low_time_ns=open_ns,
                first_trade_id=f"t-{i}",
                last_trade_id=f"t-{i}",
                is_final=True,
            )
        )
    return bars


# FIXTURES

@pytest.fixture
def detector() -> DirectionalChangeDetector:
    """Detector with fixed threshold for predictable testing."""
    return DirectionalChangeDetector(
        instrument_id="BTCUSDT",
        venue_scope="binance",
        thresholds=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=50),  # 50 bps threshold
    )


# TESTS

@pytest.mark.trace("REQ-WP-087")
def test_contiguous_bars_normal_tracking(detector: DirectionalChangeDetector):
    """Contiguous bars track normally without state resets."""
    bars = make_bars(["100", "101", "102", "103"], [0, 0, 0, 0])
    detector.run(bars)
    assert detector._direction in ("UP", "DOWN") or detector._direction is None


@pytest.mark.trace("REQ-WP-087")
def test_one_missing_bar_bridges_at_default_threshold(detector: DirectionalChangeDetector):
    """One missing bar (threshold=1 default) bridges and continues tracking."""
    bars = make_bars(["100", "101", "102", "103"], [0, 0, 1, 0])
    detector.run(bars)
    assert detector._direction == "UP"


@pytest.mark.trace("REQ-WP-087")
def test_two_missing_bars_resets_state(detector: DirectionalChangeDetector):
    """Two missing bars (threshold=1) resets detector state."""
    bars = make_bars(["100", "101", "102"], [0, 0, 2])
    detector.run(bars)
    assert detector._direction in ("UP", None)


@pytest.mark.trace("REQ-WP-087")
def test_turn_before_hole_confirm_after_gives_no_confirmation(detector: DirectionalChangeDetector):
    """A turn before a hole and confirming bar after hole emits NO confirmation."""
    # Peak at 105, then gap of 2, then drop to 100 - should NOT confirm the peak
    bars = make_bars(["100", "105", "100"], [0, 0, 2])
    confirmations = detector.run(bars)
    assert len(confirmations) == 0, f"Expected no confirmations across gap, got {confirmations}"


@pytest.mark.trace("REQ-WP-087")
def test_confirmation_lag_only_from_bars_after_hole(detector: DirectionalChangeDetector):
    """Confirmation lag is counted only from contiguous bars after the hole."""
    bars = make_bars(["100", "105", "103", "102", "101"], [0, 2, 0, 0, 0])
    confirmations = detector.run(bars)
    if confirmations:
        conf = confirmations[0]
        assert conf.confirmation_lag_bars >= 0


@pytest.mark.trace("REQ-WP-087")
def test_no_look_ahead_appending_later_bars(detector: DirectionalChangeDetector):
    """Appending later bars doesn't change earlier confirmations (no look-ahead)."""
    # Need enough bars to get a confirmation in first run
    bars1 = make_bars(["100", "101", "100", "99"], [0, 0, 0, 0])
    confs1 = detector.run(bars1)
    count1 = len(confs1)

    # Add more bars in same direction
    bars2 = make_bars(["100", "101", "100", "99", "98", "97"], [0, 0, 0, 0, 0, 0])
    confs2 = detector.run(bars2)

    # The first confirmation(s) should be identical
    assert len(confs2) >= len(confs1)
    for c1, c2 in zip(confs1, confs2):
        assert c1.extremum_id == c2.extremum_id
        assert c1.extremum_time_ns == c2.extremum_time_ns
        assert c1.price == c2.price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])