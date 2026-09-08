"""Price series with hand-identified turning points (REQ-WP-019)."""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from channelflow.bars import Bar

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1788838800000000000


def bar(index: int, close: float, *, high: float | None = None, low: float | None = None) -> Bar:
    price = Decimal(str(round(close, 8)))
    open_ns = BASE_NS + index * MINUTE_NS
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=open_ns + MINUTE_NS,
        open=price,
        high=Decimal(str(round(high if high is not None else close, 8))),
        low=Decimal(str(round(low if low is not None else close, 8))),
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


def series(closes: list[float]) -> list[Bar]:
    return [bar(i, c) for i, c in enumerate(closes)]


#: Rises to 110 at index 5, then falls. With a 200 bps (2%) threshold the
#: reversal from 110 crosses at 107.8, which first happens at index 8 (107.0).
#:
#:   idx    0    1    2    3    4     5    6    7    8    9
#:   close  100  102  105  108  109   110  109  108  107  105
PEAK_THEN_FALL = [100.0, 102.0, 105.0, 108.0, 109.0, 110.0, 109.0, 108.0, 107.0, 105.0]

#: Falls to 90 at index 5, then rises. Symmetric to the above; the reversal
#: from 90 crosses at 91.8, first at index 8 (92.0).
TROUGH_THEN_RISE = [100.0, 98.0, 95.0, 92.0, 91.0, 90.0, 91.0, 91.5, 92.0, 95.0]

#: Rises and falls by well under 2%: nothing should ever confirm.
NOISE = [100.0, 100.4, 100.1, 100.5, 100.2, 100.6, 100.3, 100.5, 100.1, 100.4]


@pytest.fixture
def peak_then_fall() -> list[Bar]:
    return series(PEAK_THEN_FALL)


@pytest.fixture
def trough_then_rise() -> list[Bar]:
    return series(TROUGH_THEN_RISE)


@pytest.fixture
def noise() -> list[Bar]:
    return series(NOISE)


def random_tail(start_index: int, count: int, *, seed: int, around: float = 105.0) -> list[Bar]:
    """Arbitrary bars to append after `t` -- PRD section 13A.28's Test A.

    Random rather than fixed: a fixed appendix could be the one continuation a
    broken detector happens to survive.
    """
    rng = random.Random(seed)
    return [bar(start_index + i, around * (1.0 + rng.uniform(-0.08, 0.08))) for i in range(count)]
