"""Buffer, snapshot, and the deltas in between (REQ-WP-004).

PRD section 11.1 steps 1 to 4: start the stream and buffer deltas, fetch a
snapshot, discard the obsolete ones, apply the rest by exact sequence.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.book import BookInvalid, BookService, BootstrapFailed, OrderBook
from channelflow.domain import BookDelta, BookSnapshot

from .conftest import delta, snapshot


@pytest.mark.trace("REQ-WP-004")
def test_bootstrap_equals_applying_only_the_deltas_after_the_snapshot(
    buffered_stream: list[BookDelta], mid_stream_snapshot: BookSnapshot
) -> None:
    """SC-001. The buffer is a convenience; it must not be a second code path."""
    service = BookService()
    for d in buffered_stream:
        service.on_delta(d)
    service.on_snapshot(mid_stream_snapshot)

    direct = OrderBook.from_snapshot(mid_stream_snapshot)
    for d in buffered_stream:
        if d.final_update_id and d.final_update_id > mid_stream_snapshot.update_id:
            direct.apply(d)

    assert service.book is not None
    assert service.book.bids == direct.bids
    assert service.book.asks == direct.asks
    assert service.health().last_sequence == direct.health().last_sequence


@pytest.mark.trace("REQ-WP-004")
def test_a_service_that_has_not_bootstrapped_refuses_every_read(
    buffered_stream: list[BookDelta],
) -> None:
    """FR-013.

    Deltas alone cannot make a book: without a snapshot there is no statement
    of what rests at the prices no delta has mentioned. Answering from the
    buffer would report a book missing every untouched level.
    """
    service = BookService()
    for d in buffered_stream:
        service.on_delta(d)

    assert not service.is_bootstrapped
    for read in (
        lambda: service.best_bid_ask(),
        lambda: service.top(3),
        lambda: service.depth_within_bps(10),
    ):
        with pytest.raises(BookInvalid):
            read()


@pytest.mark.trace("REQ-WP-004")
def test_a_buffer_that_does_not_reach_the_snapshot_fails_bootstrap() -> None:
    """The spec's third US1 scenario.

    The snapshot is at 100 and the buffer resumes at 104: deltas 101 to 103
    were never seen. Applying 104 onto the snapshot would produce a book that
    looks healthy and is wrong at every level those three deltas touched.
    """
    service = BookService()
    service.on_delta(delta(104, 104, bids=[("98", "2")]))

    with pytest.raises(BootstrapFailed):
        service.on_snapshot(snapshot(100))

    assert not service.is_bootstrapped
    assert service.needs_snapshot


@pytest.mark.trace("REQ-WP-004")
def test_a_snapshot_newer_than_every_buffered_delta_bootstraps_on_its_own() -> None:
    """A snapshot ahead of the buffer is not a failure: every buffered delta is
    obsolete, and the snapshot is a complete book by itself."""
    service = BookService()
    service.on_delta(delta(98, 98, bids=[("99", "5")]))
    service.on_snapshot(snapshot(120, bids=[("100", "3")], asks=[("101", "2")]))

    assert service.is_bootstrapped
    assert service.best_bid_ask() == (Decimal("100"), Decimal("101"))
    assert service.health().last_sequence == 120


@pytest.mark.trace("REQ-WP-004")
def test_deltas_arriving_after_bootstrap_apply_directly(
    buffered_stream: list[BookDelta], mid_stream_snapshot: BookSnapshot
) -> None:
    """The buffer is for the bootstrap window only, not a permanent queue."""
    service = BookService()
    service.on_snapshot(mid_stream_snapshot)
    for d in buffered_stream:
        service.on_delta(d)

    assert service.is_bootstrapped
    assert service.health().last_sequence == 104
    assert service.health().gap_count == 0
