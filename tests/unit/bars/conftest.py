"""Trade construction helpers for bar tests (REQ-WP-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import EventMeta, TradeEvent

MINUTE_NS = 60 * 1_000_000_000
#: Aligned to a minute boundary, so `BASE_NS` really is a window start and the
#: arithmetic in the tests means what it reads as. 1788800000s is not on a
#: minute; assuming it was produced three test failures that looked like
#: builder bugs and were not.
BASE_NS = (1788800000 // 60) * 60 * 1_000_000_000


def make_trade(
    *,
    event_time_ns: int,
    price: str,
    qty: str,
    side: str = "buy",
    trade_id: str | None = None,
    ingest_offset_ns: int = 5_000_000,
) -> TradeEvent:
    """A trade whose ingest time is deliberately later than its event time,
    so a builder that confused the two would produce visibly wrong windows."""
    return TradeEvent(
        meta=EventMeta(
            source="test",
            venue="binance",
            market_type="spot",
            symbol="BTCUSDT",
            event_time_ns=event_time_ns,
            ingest_time_ns=event_time_ns + ingest_offset_ns,
            sequence=None,
            source_event_id=None,
        ),
        trade_id=trade_id or f"t-{event_time_ns}",
        price=Decimal(price),
        qty_base=Decimal(qty),
        notional_quote=Decimal(price) * Decimal(qty),
        aggressor_side=side,  # type: ignore[arg-type]
        is_buyer_maker=(side == "sell"),
    )


@pytest.fixture
def base_ns() -> int:
    return BASE_NS
