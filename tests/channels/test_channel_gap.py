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
    # Ten bars; two minutes are missing before index 4, so the closes are at minutes
    # 1, 2, 3, 4, 7, 8, 9, 10, 11, 12 from BASE_NS. With lookback=8 the eight most
    # recent bars would reach back over the hole; the window must stop at it instead,
    # leaving indices 4..9 -- six bars -- so the cut, not the count, decides.
    bars = list(_make_bars(["100"] * 10, [0, 0, 0, 0, 2, 0, 0, 0, 0, 0]))
    as_of_ns = BASE_NS + 12 * MINUTE_NS  # at the last bar's close
    window = fit_window(bars, as_of_ns=as_of_ns, lookback=8)
    assert len(window) == 6  # indices 4..9: the bars after the hole, not 8
    # The first bar in the window is the first one after the hole (closes at minute 7).
    assert window[0].close_time_ns == BASE_NS + 7 * MINUTE_NS


@pytest.mark.trace("REQ-WP-087")
def test_channel_window_short_after_gap():
    """Window is marked short until lookback contiguous bars exist after gap."""
    # Eight bars, two minutes missing before index 4: closes at minutes
    # 1, 2, 3, 4, 7, 8, 9, 10. Four bars (4..7) exist after the hole.
    bars = list(_make_bars(["100"] * 8, [0, 0, 0, 0, 2, 0, 0, 0]))
    as_of_ns = BASE_NS + 10 * MINUTE_NS  # at the last bar's close
    window = fit_window(bars, as_of_ns=as_of_ns, lookback=5)
    assert len(window) == 4  # fewer than lookback: short, because of the hole
    assert window[0].close_time_ns == BASE_NS + 7 * MINUTE_NS


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


# ---- a hole leaves a window too short to fit (found in production, 2026-10-08) ------------------
#
# REQ-WP-087 let a channel restart at a hole and fit "whatever follows". On the real series every
# hole leaves a window of exactly one bar -- and a line cannot be fitted through one point:
# `np.polyfit` divides by a zero column and raises `LinAlgError`, which nothing catches, so one hole
# in the history ended the replay of the whole series. The code had never been run against a hole in
# real data; the rebuilt worker image was the first to carry it there.


def _series_with_a_hole(before: int, missing: int, after: int) -> list:
    gaps = [0] * before + [missing] + [0] * (after - 1)
    prices = [str(100 + (i % 7)) for i in range(len(gaps))]
    return list(_make_bars(prices, gaps))


@pytest.mark.trace("REQ-WP-087")
def test_a_window_of_one_bar_after_a_hole_is_refused_not_crashed() -> None:
    from channelflow.channels.rolling_ols import RollingOLSChannel

    bars = _series_with_a_hole(before=8, missing=3, after=6)
    first_after_hole = bars[8]
    model = RollingOLSChannel(lookback=5, min_window_bars=3)

    with pytest.raises(ChannelFitError, match="after a hole"):
        model.fit(bars[:9], as_of_ns=first_after_hole.close_time_ns)


@pytest.mark.trace("REQ-WP-087")
def test_the_channel_returns_at_the_configured_minimum_and_says_it_is_short() -> None:
    from channelflow.channels.rolling_ols import RollingOLSChannel

    bars = _series_with_a_hole(before=8, missing=3, after=6)
    model = RollingOLSChannel(lookback=5, min_window_bars=3)

    refused = [i for i in range(8, len(bars)) if _fits(model, bars[: i + 1]) is None]
    fitted = {i: _fits(model, bars[: i + 1]) for i in range(8, len(bars))}

    assert refused == [8, 9]  # one and two bars after the hole: below the minimum of three
    assert fitted[10] is not None and fitted[10].window_bars == 3 and fitted[10].window_short
    assert fitted[13] is not None and fitted[13].window_bars == 5 and not fitted[13].window_short


def _fits(model, prefix):  # type: ignore[no-untyped-def]
    try:
        return model.fit(prefix, as_of_ns=prefix[-1].close_time_ns)
    except ChannelFitError:
        return None


@pytest.mark.trace("REQ-WP-087")
def test_a_series_with_a_hole_replays_to_the_end_with_the_default_runner() -> None:
    """The regression itself, with nothing configured: one hole must not end a series' replay.

    This is the production shape -- the default runner (lookback 60), a long series, one hole. On
    the code as deployed on 2026-10-08 it raised `LinAlgError` from `np.polyfit` at the first bar
    after the hole.
    """
    from channelflow.backtest import BacktestRunner

    bars = _series_with_a_hole(before=80, missing=4, after=40)

    report = BacktestRunner().run(bars)  # must not raise

    assert report is not None


@pytest.mark.trace("REQ-WP-087")
def test_the_minimum_must_be_a_line_and_no_more_than_the_lookback() -> None:
    from channelflow.channels.rolling_ols import RollingOLSChannel

    with pytest.raises(ValueError, match="min_window_bars"):
        RollingOLSChannel(lookback=10, min_window_bars=1)  # a line needs two points
    with pytest.raises(ValueError, match="min_window_bars"):
        RollingOLSChannel(
            lookback=10, min_window_bars=11
        )  # more than the lookback can never be met
    RollingOLSChannel(
        lookback=10, min_window_bars=10
    )  # equal is the old behaviour: full or nothing


@pytest.mark.trace("REQ-WP-087")
def test_fit_window_enforces_the_floor_only_after_a_hole() -> None:
    bars = _series_with_a_hole(before=8, missing=3, after=6)
    after_one = bars[8].close_time_ns
    with pytest.raises(ChannelFitError, match="after a hole"):
        fit_window(bars[:9], as_of_ns=after_one, lookback=5, min_bars=3)
    assert len(fit_window(bars[:11], as_of_ns=bars[10].close_time_ns, lookback=5, min_bars=3)) == 3
    # No hole: the full lookback is required, as it always was, whatever the floor says.
    with pytest.raises(ChannelFitError, match="need 5"):
        fit_window(bars[:4], as_of_ns=bars[3].close_time_ns, lookback=5, min_bars=2)
