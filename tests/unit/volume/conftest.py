"""Trades at known prices (REQ-WP-012)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import EventMeta, TradeEvent

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1788838800000000000


def trade(
    index: int, price: str, qty: str, side: str = "buy", *, at: int | None = None
) -> TradeEvent:
    at_ns = BASE_NS + (index if at is None else at) * MINUTE_NS
    return TradeEvent(
        meta=EventMeta(
            source="test",
            venue="binance",
            market_type="spot",
            symbol="BTCUSDT",
            event_time_ns=at_ns,
            ingest_time_ns=at_ns + 1,
        ),
        trade_id=f"t-{index}",
        price=Decimal(price),
        qty_base=Decimal(qty),
        notional_quote=Decimal(price) * Decimal(qty),
        aggressor_side=side,  # type: ignore[arg-type]
    )


@pytest.fixture
def shelved() -> list[TradeEvent]:
    """A profile with a clear shelf at 100-101 and thin wings.

    Bin width 1, anchored at 98:
      98-99   : 1     99-100 : 2     100-101: 20 (the shelf, and the POC)
      101-102 : 2     102-103: 1
    Total 26; 70% of it is 18.2, which the POC alone (20) already exceeds.
    """
    return [
        trade(0, "98.5", "1"),
        trade(1, "99.5", "2"),
        trade(2, "100.5", "20"),
        trade(3, "101.5", "2"),
        trade(4, "102.5", "1"),
    ]


@pytest.fixture
def bimodal() -> list[TradeEvent]:
    """Two shelves with a thin gap, and the POC between them.

    Bin volumes 10, 1, 20, 1, 10; total 42, so 70% is 29.4.

      expansion from the POC -> {0, 1, 2}, contiguous
      descending volume      -> {0, 2, 4}, with a hole at 1 and 3

    Both hold more than 70%. Only this shape tells the two rules apart, which
    is why it exists: on a single-peaked profile every construction agrees, and
    a test built on one would pass whichever was implemented.
    """
    return [
        trade(0, "100.5", "10"),
        trade(1, "101.5", "1"),
        trade(2, "102.5", "20"),
        trade(3, "103.5", "1"),
        trade(4, "104.5", "10"),
    ]


@pytest.fixture
def ramp() -> list[TradeEvent]:
    """Ten bins rising 1 to 10.

    No bin is 1.8x its immediate neighbours, so a neighbour-relative detector
    finds nothing. Measured against the whole profile's mean of 5.5, the top
    bin is 1.8x and the bottom is 0.18x -- so a detector comparing to the
    global average finds two nodes here. Only a profile longer than the
    neighbour window can tell the two apart.
    """
    return [trade(i, f"{100 + i}.5", str(i + 1)) for i in range(10)]


@pytest.fixture
def uniform() -> list[TradeEvent]:
    """Five bins of equal volume: no shelves, no gaps."""
    return [trade(i, f"{100 + i}.5", "10") for i in range(5)]
