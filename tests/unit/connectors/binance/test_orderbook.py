"""Order-book reconstruction against recorded traffic (REQ-WP-003).

PRD section 11.1 gives the procedure and section 8.1 forbids hiding sequence
gaps. These tests replay 30 consecutive recorded deltas, then break the sequence
on purpose -- a reconstruction that has never been shown to detect a gap is a
claim, not a guarantee.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from channelflow.book import BookInvalid, OrderBook
from channelflow.connectors.binance import normalize as n
from channelflow.domain import PriceLevel

INGEST = 1788838909900000000


def _deltas(raw_updates: list[dict[str, Any]]) -> list[Any]:
    return [
        n.depth_update(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)
        for raw in raw_updates
    ]


@pytest.mark.trace("REQ-WP-003")
def test_the_recorded_sequence_leaves_the_book_valid(depth_updates: list[dict[str, Any]]) -> None:
    """SC-004. The capture has zero gaps, so a correct book stays valid."""
    deltas = _deltas(depth_updates)
    book = OrderBook.from_first_delta(deltas[0])
    for delta in deltas[1:]:
        book.apply(delta)

    assert book.health.valid
    assert book.health.gap_count == 0
    assert book.health.last_sequence == deltas[-1].final_update_id


@pytest.mark.trace("REQ-WP-003")
def test_a_missing_delta_makes_the_book_admit_it_is_broken(
    depth_updates: list[dict[str, Any]],
) -> None:
    """SC-005. The important half: the book must notice, not carry on.

    PRD section 8.1: do not hide sequence gaps. A book that silently applies an
    out-of-order delta diverges from the venue while still reporting good health.
    """
    deltas = _deltas(depth_updates)
    book = OrderBook.from_first_delta(deltas[0])
    book.apply(deltas[1])

    before = book.health.last_sequence
    book.apply(deltas[3])  # deltas[2] deliberately skipped

    assert not book.health.valid
    assert book.health.gap_count == 1
    assert book.health.last_sequence == before, "the out-of-order delta must not be applied"


@pytest.mark.trace("REQ-WP-003")
def test_an_invalid_book_refuses_to_supply_state(depth_updates: list[dict[str, Any]]) -> None:
    """SC-006. PRD section 11.1 rule 6 forbids emitting features from a stale
    book. Refusing here means no caller has to remember the rule."""
    deltas = _deltas(depth_updates)
    book = OrderBook.from_first_delta(deltas[0])
    book.apply(deltas[3])  # gap

    assert not book.health.valid
    with pytest.raises(BookInvalid):
        book.best_bid_ask()


@pytest.mark.trace("REQ-WP-003")
def test_a_zero_quantity_level_removes_the_rung(depth_updates: list[dict[str, Any]]) -> None:
    """FR-011. Zero quantity is how the venue says a price level is gone."""
    deltas = _deltas(depth_updates)
    book = OrderBook.from_first_delta(deltas[0])

    price = next(iter(book.bids))
    assert price in book.bids

    book.apply(
        deltas[1].model_copy(
            update={"bids": (PriceLevel(price=price, qty=Decimal("0")),), "asks": ()}
        )
    )
    assert price not in book.bids


@pytest.mark.trace("REQ-WP-003")
def test_deltas_older_than_the_snapshot_are_discarded(
    depth_updates: list[dict[str, Any]], depth_snapshot: dict[str, Any]
) -> None:
    """PRD section 11.1 step 3. Buffered deltas that predate the snapshot
    describe a book state the snapshot already includes."""
    snapshot = n.depth_snapshot(
        depth_snapshot,
        venue="binance",
        market_type="spot",
        symbol="BTCUSDT",
        ingest_time_ns=INGEST,
    )
    deltas = _deltas(depth_updates)

    book = OrderBook.from_snapshot(snapshot)
    stale = deltas[0].model_copy(update={"first_update_id": 1, "final_update_id": 2})
    book.apply(stale)

    assert book.health.valid, "an obsolete delta is discarded, not a gap"
    assert book.health.gap_count == 0
    assert book.health.last_sequence == snapshot.update_id
