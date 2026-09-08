"""Bar series builders for channel tests (REQ-WP-006)."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from channelflow.bars import Bar

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = (1788800000 // 60) * 60 * 1_000_000_000


def make_bar(*, index: int, close: float, is_final: bool = True) -> Bar:
    price = Decimal(str(round(close, 8)))
    open_ns = BASE_NS + index * MINUTE_NS
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=open_ns + MINUTE_NS,
        open=price,
        high=price,
        low=price,
        close=price,
        volume_base=Decimal("1"),
        volume_quote=price,
        trade_count=1,
        aggressive_buy_base=Decimal("1"),
        aggressive_sell_base=Decimal("0"),
        delta_base=Decimal("1"),
        vwap=price,
        high_time_ns=open_ns,
        low_time_ns=open_ns,
        first_trade_id=f"t-{index}",
        last_trade_id=f"t-{index}",
        is_final=is_final,
    )


def log_linear_series(
    n: int,
    *,
    start: float = 100.0,
    slope_per_bar: float = 0.001,
    noise: float = 0.0,
    index_offset: int = 0,
) -> list[Bar]:
    """A series whose log price is a straight line, optionally with noise.

    Deterministic noise from a fixed sequence rather than a random generator:
    a channel test that changes between runs cannot distinguish a regression
    from a reseed.
    """
    bars = []
    for i in range(n):
        wobble = noise * math.sin(i * 1.7) if noise else 0.0
        bars.append(
            make_bar(
                index=index_offset + i,
                close=start * math.exp(slope_per_bar * i + wobble),
            )
        )
    return bars


@pytest.fixture
def trending() -> list[Bar]:
    return log_linear_series(120, slope_per_bar=0.001, noise=0.004)
