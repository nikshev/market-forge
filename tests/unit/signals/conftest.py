"""Bars and channels positioned where a test wants them (REQ-WP-007)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar
from channelflow.channels import ChannelQuality, ChannelSnapshot

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = (1788800000 // 60) * 60 * 1_000_000_000

LOWER, UPPER = 100.0, 200.0


def bar_at(position: float, *, index: int) -> Bar:
    """A bar whose close sits at a chosen channel position.

    Building bars from the position rather than from a price keeps every test
    about the state machine instead of about arithmetic.
    """
    close = Decimal(str(LOWER + position * (UPPER - LOWER)))
    open_ns = BASE_NS + index * MINUTE_NS
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=open_ns + MINUTE_NS,
        open=close,
        high=close,
        low=close,
        close=close,
        volume_base=Decimal("1"),
        volume_quote=close,
        trade_count=1,
        aggressive_buy_base=Decimal("1"),
        aggressive_sell_base=Decimal("0"),
        delta_base=Decimal("1"),
        vwap=close,
        high_time_ns=open_ns,
        low_time_ns=open_ns,
        first_trade_id=f"t-{index}",
        last_trade_id=f"t-{index}",
        is_final=True,
    )


def channel(*, slope: float = -0.5, quality: float = 0.8, index: int = 0) -> ChannelSnapshot:
    as_of = BASE_NS + index * MINUTE_NS + MINUTE_NS
    return ChannelSnapshot(
        as_of_ns=as_of,
        model_name="test",
        model_version="1.0.0",
        lookback=60,
        center_now=(LOWER + UPPER) / 2,
        upper_now=UPPER,
        lower_now=LOWER,
        slope_normalized=slope,
        width_pct=100.0,
        quality=ChannelQuality(
            score=quality,
            submetrics={"coverage_score": quality},
            contributing=("coverage_score",),
            unavailable=(),
        ),
        source_max_event_time_ns=as_of,
    )


@pytest.fixture
def bearish():
    return channel(slope=-0.5, quality=0.8)
