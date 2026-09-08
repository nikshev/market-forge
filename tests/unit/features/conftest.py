"""Constructed books and trades (REQ-WP-011).

Every expected value in these tests is arithmetic done by hand and written as a
literal. A feature asserted against a second implementation of its own formula
passes whenever both copies are wrong the same way.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.book import BookService
from channelflow.domain import BookDelta, BookSnapshot, EventMeta, PriceLevel, TradeEvent

SECOND_NS = 1_000_000_000
BASE_NS = 1788838900000000000


def meta(event_time_ns: int) -> EventMeta:
    return EventMeta(
        source="test",
        venue="binance",
        market_type="spot",
        symbol="BTCUSDT",
        event_time_ns=event_time_ns,
        ingest_time_ns=event_time_ns + 5 * SECOND_NS,
    )


def levels(pairs: list[tuple[str, str]]) -> tuple[PriceLevel, ...]:
    return tuple(PriceLevel(price=Decimal(p), qty=Decimal(q)) for p, q in pairs)


def snapshot(
    update_id: int,
    bids: list[tuple[str, str]],
    asks: list[tuple[str, str]],
    *,
    at_ns: int | None = None,
) -> BookSnapshot:
    return BookSnapshot(
        meta=meta(at_ns if at_ns is not None else BASE_NS),
        update_id=update_id,
        bids=levels(bids),
        asks=levels(asks),
    )


def book_of(
    bids: list[tuple[str, str]], asks: list[tuple[str, str]], *, at_ns: int | None = None
) -> BookService:
    service = BookService()
    service.on_snapshot(snapshot(1, bids, asks, at_ns=at_ns))
    return service


def trade(
    trade_id: str,
    price: str,
    qty: str,
    side: str,
    *,
    at_ns: int,
) -> TradeEvent:
    return TradeEvent(
        meta=meta(at_ns),
        trade_id=trade_id,
        price=Decimal(price),
        qty_base=Decimal(qty),
        notional_quote=Decimal(price) * Decimal(qty),
        aggressor_side=side,  # type: ignore[arg-type]
    )


def gapping_delta(*, at_ns: int | None = None) -> BookDelta:
    """A delta that skips the sequence, so the book refuses everything after it."""
    return BookDelta(
        meta=meta(at_ns if at_ns is not None else BASE_NS + SECOND_NS),
        first_update_id=99,
        final_update_id=99,
    )


@pytest.fixture
def lopsided() -> BookService:
    """bid 100 x 2, ask 101 x 6.

    mid       = 100.5
    QI        = (2 - 6) / 8            = -0.5
    microprice= (100*6 + 101*2) / 8    = 100.25
    spread    = (100.25 - 100.5)/100.5 * 10_000 = -24.8756... bps
    """
    return book_of([("100", "2")], [("101", "6")])


@pytest.fixture
def balanced() -> BookService:
    """Equal queues: the microprice must sit exactly on the mid."""
    return book_of([("100", "3")], [("101", "3")])
