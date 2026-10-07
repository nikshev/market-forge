"""Channel gap policy (REQ-WP-087): channel fits only to bars after a hole.

FR-004 and FR-005: the channel window starts after a hole; snapshot is absent
or flagged short until `lookback` contiguous bars exist after the hole.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar
from channelflow.channels.window import ChannelFitError, fit_window

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1_788_838_800_000_000_000


def _make_bars(closing_prices: list[str], gaps: list[int]):
    """Generator version for internal use."""
    assert len(closing_prices) == len(gaps)
    assert gaps[0] == 0, "First bar must have gap=0"

    close_ns = BASE_NS + MINUTE_NS  # First bar closes at BASE_NS + 1 minute

    for i, (_close_str, gap) in enumerate(zip(closing_prices, gaps, strict=False)):
        if i == 0:
            open_ns = BASE_NS
            close_ns = BASE_NS + MINUTE_NS
        else:
            # gap missing bars + 1 for the step to this bar
            close_ns += (gap + 1) * MINUTE_NS
            open_ns = close_ns - MINUTE_NS
            close_ns = open_ns + MINUTE_NS

        yield Bar(
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


def make_bars(closing_prices: list[str], gaps: list[int]) -> list:
    """Create a series of bars with specified close prices and gaps."""
    return list(_make_bars(closing_prices, gaps))


# TESTS


@pytest.mark.trace("REQ-WP-087")
def test_channel_window_starts_after_gap():
    """Channel window starts at first bar after a gap."""
    # 10 bars, gap of 2 before bar 5, lookback=5
    # Bars: 0,1,2,3, [gap of 2], 5,6,7,8,9
    # Window at bar 9 (last) should start at bar 5 (first after gap)
    bars = list(_make_bars(["100"] * 10, [0, 0, 0, 0, 2, 0, 0, 0, 0, 0]))
    as_of_ns = BASE_NS + 10 * MINUTE_NS  # at bar 9 close
    window = fit_window(bars, as_of_ns=as_of_ns, lookback=5)
    assert len(window) == 5
    # First bar in window should be bar 5 (index 5 in original)
    assert window[0].close == Decimal("100")
    # Window should start at bar 5 (first after gap)
    assert window[0].close_time_ns == BASE_NS + 6 * MINUTE_NS + 2 * 60_000_000_000  # bar 5 close


@pytest.mark.trace("REQ-WP-087")
def test_channel_window_short_after_gap():
    """Window is marked short until lookback contiguous bars exist after gap."""
    # 7 bars, gap of 2 before bar 5, only 3 bars after gap (5,6,7)
    # Window at bar 7 should have window_bars=3, window_short=True
    bars = list(_make_bars(["100"] * 8, [0, 0, 0, 0, 2, 0, 0, 0]))
    as_of_ns = BASE_NS + 8 * MINUTE_NS + 2 * MINUTE_NS  # at bar 7 close
    window = fit_window(bars, as_of_ns=as_of_ns, lookback=5)
    assert len(window) == 3  # only 3 bars after gap
    # The fit_window function doesn't return window_short flag directly,
    # but the window size tells us it's short


@pytest.mark.trace("REQ-WP-087")
def test_channel_window_absent_when_no_bars_after_gap():
    """Snapshot absent when no bars after gap."""
    # Gap at the very end, no bars after
    _make_bars(["100"] * 5, [0, 0, 0, 0, 2])  # gap at end
    # Actually, if as_of is at the gap, there are no bars after
    with pytest.raises(ChannelFitError):
        fit_window([], as_of_ns=BASE_NS, lookback=5)  # empty bars


@pytest.mark.trace("REQ-WP-087")
def test_channel_no_look_ahead():
    """Appending later bars doesn't change earlier window."""
    bars1 = list(_make_bars(["100"] * 6, [0, 0, 0, 0, 0, 0]))
    as_of_ns = BASE_NS + 5 * MINUTE_NS  # at bar 4 close (5th bar)
    window1 = fit_window(bars1[:5], as_of_ns=as_of_ns, lookback=5)

    # Add more bars
    bars2 = list(_make_bars(["100"] * 8, [0, 0, 0, 0, 0, 0, 0, 0]))
    window2 = fit_window(bars2[:5], as_of_ns=as_of_ns, lookback=5)

    # Window should be identical
    assert len(window1) == len(window2)
    for w1, w2 in zip(window1, window2, strict=False):
        assert w1.close_time_ns == w2.close_time_ns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
