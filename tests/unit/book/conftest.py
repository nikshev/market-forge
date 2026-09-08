"""Hand-built deltas and snapshots (REQ-WP-004).

Constructed rather than recorded: the bootstrap rules are about sequence
numbers, and a recorded stream has exactly one sequence history. The recorded
Binance stream is exercised separately, in the connector's own tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import BookDelta, BookSnapshot, EventMeta, PriceLevel

SECOND_NS = 1_000_000_000
BASE_NS = 1788838900000000000


def meta(event_time_ns: int) -> EventMeta:
    return EventMeta(
        source="test",
        venue="binance",
        market_type="spot",
        symbol="BTCUSDT",
        event_time_ns=event_time_ns,
        ingest_time_ns=event_time_ns + 1_000_000,
    )


def levels(pairs: list[tuple[str, str]]) -> tuple[PriceLevel, ...]:
    return tuple(PriceLevel(price=Decimal(p), qty=Decimal(q)) for p, q in pairs)


def delta(
    first: int,
    final: int,
    *,
    bids: list[tuple[str, str]] | None = None,
    asks: list[tuple[str, str]] | None = None,
    at_ns: int | None = None,
) -> BookDelta:
    return BookDelta(
        meta=meta(at_ns if at_ns is not None else BASE_NS + final * SECOND_NS),
        first_update_id=first,
        final_update_id=final,
        bids=levels(bids or []),
        asks=levels(asks or []),
    )


def snapshot(
    update_id: int,
    *,
    bids: list[tuple[str, str]] | None = None,
    asks: list[tuple[str, str]] | None = None,
    at_ns: int | None = None,
) -> BookSnapshot:
    # `is None` rather than `or`: an explicitly empty side is a book with one
    # side empty, which several tests are specifically about. Falling back to a
    # default there would quietly test something else.
    return BookSnapshot(
        meta=meta(at_ns if at_ns is not None else BASE_NS + update_id * SECOND_NS),
        update_id=update_id,
        bids=levels([("100", "1")] if bids is None else bids),
        asks=levels([("101", "1")] if asks is None else asks),
    )


@pytest.fixture
def buffered_stream() -> list[BookDelta]:
    """Deltas 98 through 104, straddling the snapshot at 100 below."""
    return [
        delta(98, 98, bids=[("99", "5")]),
        delta(99, 99, asks=[("102", "5")]),
        delta(100, 100, bids=[("100", "9")]),
        delta(101, 101, bids=[("98", "2")]),
        delta(102, 102, asks=[("103", "3")]),
        delta(103, 103, bids=[("99", "0")]),
        delta(104, 104, asks=[("101", "4")]),
    ]


@pytest.fixture
def mid_stream_snapshot() -> BookSnapshot:
    """Taken at 100: deltas 98-100 are already in it, 101 onward are not."""
    return snapshot(100, bids=[("100", "9"), ("99", "5")], asks=[("101", "1"), ("102", "5")])
