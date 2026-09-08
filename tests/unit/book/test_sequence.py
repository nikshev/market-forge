"""A gap stops the book, and only a snapshot restarts it (REQ-WP-004).

PRD section 8.1 forbids hiding sequence gaps; section 11.1 rule 6 forbids
emitting anything from an invalid book. Both are refusals, and a refusal that
quietly stops refusing looks exactly like a passing suite -- so each one here
is checked from the outside, by what the service will and will not answer.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.book import BookInvalid, BookService, BootstrapFailed

from .conftest import delta, snapshot


def _bootstrapped() -> BookService:
    service = BookService()
    service.on_snapshot(snapshot(100, bids=[("100", "9")], asks=[("101", "4")]))
    service.on_delta(delta(101, 101, bids=[("99", "5")]))
    return service


@pytest.mark.trace("REQ-WP-004")
def test_a_delta_that_breaks_the_sequence_changes_nothing() -> None:
    """SC-002. Not applied, not partially applied, not applied out of order."""
    service = _bootstrapped()
    before_bids = dict(service.book.bids) if service.book else {}
    before_asks = dict(service.book.asks) if service.book else {}

    service.on_delta(delta(105, 105, bids=[("97", "50")], asks=[("110", "50")]))

    assert service.book is not None
    assert service.book.bids == before_bids
    assert service.book.asks == before_asks
    assert service.health().last_sequence == 101, "the refused delta must not advance it"


@pytest.mark.trace("REQ-WP-004")
def test_a_gap_is_counted_once_and_reported() -> None:
    """PRD section 8.1. Counted once: a gap seen by the live book was, for a
    while, added to the service's own tally as well, and health reported two."""
    service = _bootstrapped()
    service.on_delta(delta(105, 105))

    health = service.health()
    assert not health.valid
    assert health.gap_count == 1


@pytest.mark.trace("REQ-WP-004")
def test_every_read_refuses_after_a_gap() -> None:
    """FR-005, PRD section 11.1 rule 6.

    Each read is listed explicitly rather than trusting a shared guard: the
    guard is the thing under test, and a read added later that bypasses it is
    exactly what this must catch.
    """
    service = _bootstrapped()
    service.on_delta(delta(105, 105))

    for name, read in (
        ("best_bid_ask", lambda: service.best_bid_ask()),
        ("top", lambda: service.top(5)),
        ("depth_within_bps", lambda: service.depth_within_bps(25)),
    ):
        with pytest.raises(BookInvalid, match="gap"):
            read()
            pytest.fail(f"{name} answered from a book that has diverged")


@pytest.mark.trace("REQ-WP-004")
def test_a_fresh_snapshot_rebuilds_the_book_and_the_gap_survives() -> None:
    """SC-003, FR-006.

    The gap count is history, not a status flag. A book that reset it on every
    rebuild would report perfect health while flapping once a second.
    """
    service = _bootstrapped()
    service.on_delta(delta(105, 105))
    assert service.needs_snapshot

    service.rebuild(snapshot(200, bids=[("100", "3")], asks=[("101", "2")]))

    assert not service.needs_snapshot
    assert service.best_bid_ask() == (Decimal("100"), Decimal("101"))
    health = service.health()
    assert health.valid
    assert health.last_sequence == 200
    assert health.gap_count == 1, "the rebuild must not erase the history"


@pytest.mark.trace("REQ-WP-004")
def test_gaps_accumulate_across_rebuilds() -> None:
    """Two gaps and two rebuilds leave a count of two."""
    service = _bootstrapped()
    service.on_delta(delta(105, 105))
    service.rebuild(snapshot(200))
    service.on_delta(delta(400, 400))
    service.rebuild(snapshot(500))

    assert service.health().gap_count == 2


@pytest.mark.trace("REQ-WP-004")
def test_a_delta_with_no_sequence_range_is_refused() -> None:
    """The spec's first edge case. A delta whose position is unknown cannot be
    validated, and applying it would break the guarantee everything rests on."""
    service = _bootstrapped()
    unpositioned = delta(102, 102).model_copy(
        update={"first_update_id": None, "final_update_id": None}
    )

    with pytest.raises(BookInvalid):
        service.on_delta(unpositioned)


@pytest.mark.trace("REQ-WP-004")
def test_an_obsolete_delta_is_discarded_rather_than_counted_as_a_gap() -> None:
    """A delta the snapshot already covers is old news, not a break."""
    service = _bootstrapped()
    service.on_delta(delta(50, 50, bids=[("97", "50")]))

    health = service.health()
    assert health.valid
    assert health.gap_count == 0
    assert Decimal("97") not in (service.book.bids if service.book else {})


@pytest.mark.trace("REQ-WP-004")
def test_a_buffer_with_its_own_gap_fails_the_bootstrap() -> None:
    """Not every buffer can bootstrap a snapshot, even when its first delta
    connects: 101 follows the snapshot, 103 does not follow 101."""
    service = BookService()
    service.on_delta(delta(101, 101, bids=[("99", "5")]))
    service.on_delta(delta(103, 103, bids=[("98", "2")]))

    with pytest.raises(BootstrapFailed):
        service.on_snapshot(snapshot(100))

    assert not service.is_bootstrapped
