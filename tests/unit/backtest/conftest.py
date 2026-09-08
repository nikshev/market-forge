"""A bar series that actually exercises the lifecycle (REQ-WP-010)."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from channelflow.bars import Bar

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = (1788800000 // 60) * 60 * 1_000_000_000

#: Bars before the first channel can be fitted. The default lookback is 60, so
#: nothing happens before then however the prices move.
WARMUP_BARS = 60
#: One break every this many bars. Long enough for a channel to re-form.
BREAK_PERIOD = 90


def bar(index: int, close: float) -> Bar:
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
        is_final=True,
    )


@pytest.fixture
def falling_with_breakouts() -> list[Bar]:
    """A declining channel, price pushing at its upper edge, breaking down often.

    The breaks are what make this a lifecycle fixture rather than an opening
    fixture. Without them the first confirmed candidate holds the machine for
    the rest of the series (FR-014 allows one at a time, and nothing yet
    resolves a confirmation -- see ADR-010), so a parity test over the result
    would compare a single candidate and prove almost nothing.

    Deterministic by construction: a backtest fixture built from a random
    generator cannot distinguish a regression from a different draw.
    """
    bars = []
    for i in range(400):
        drift = -0.0015 * i
        oscillation = 0.02 * math.sin(i * 0.55)
        breaking = -0.10 if i > WARMUP_BARS and i % BREAK_PERIOD < 4 else 0.0
        bars.append(bar(i, 100.0 * math.exp(drift + oscillation + breaking)))
    return bars
