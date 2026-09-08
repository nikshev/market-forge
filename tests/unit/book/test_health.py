"""What the book says about itself (REQ-WP-004).

PRD section 11.1 requires the status structure. ADR-012 drops its `latency_ms`
-- that measures transport, not reconstruction -- and makes `stale_ms` event-time
arithmetic, so the same recorded stream reports the same health on every replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.book import BookService
from channelflow.domain import BookSnapshot

from .conftest import BASE_NS, SECOND_NS, delta, snapshot


@pytest.mark.trace("REQ-WP-004")
def test_health_is_reported_at_every_stage_of_the_lifecycle() -> None:
    """SC-005. Bootstrap, gap, rebuild -- each has an answer, none is silent."""
    service = BookService()

    fresh = service.health()
    assert not fresh.valid, "a service with no book cannot be trusted"
    assert fresh.last_sequence == 0

    service.on_snapshot(snapshot(100))
    service.on_delta(delta(101, 101, bids=[("99", "5")]))
    after_bootstrap = service.health()
    assert after_bootstrap.valid
    assert after_bootstrap.last_sequence == 101
    assert after_bootstrap.gap_count == 0

    service.on_delta(delta(105, 105))
    after_gap = service.health()
    assert not after_gap.valid
    assert after_gap.gap_count == 1
    assert after_gap.last_sequence == 101

    service.rebuild(snapshot(200))
    after_rebuild = service.health()
    assert after_rebuild.valid
    assert after_rebuild.gap_count == 1
    assert after_rebuild.last_sequence == 200


@pytest.mark.trace("REQ-WP-004")
def test_staleness_is_the_distance_from_the_last_applied_event() -> None:
    """FR-010. Event time in, event time out -- no clock anywhere in between."""
    service = BookService()
    service.on_snapshot(snapshot(100, at_ns=BASE_NS))
    service.on_delta(delta(101, 101, at_ns=BASE_NS + 3 * SECOND_NS))

    assert service.health(as_of_ns=BASE_NS + 3 * SECOND_NS).stale_ns == 0
    assert service.health(as_of_ns=BASE_NS + 8 * SECOND_NS).stale_ns == 5 * SECOND_NS


@pytest.mark.trace("REQ-WP-004")
def test_staleness_is_zero_rather_than_negative_when_asked_about_the_past() -> None:
    """A book cannot be less than fresh. Asking about an earlier event time is
    a caller's mistake, and a negative staleness would read as the book being
    ahead of the data."""
    service = BookService()
    service.on_snapshot(snapshot(100, at_ns=BASE_NS + 10 * SECOND_NS))

    assert service.health(as_of_ns=BASE_NS).stale_ns == 0


@pytest.mark.trace("REQ-WP-004")
def test_staleness_is_not_reported_when_it_was_not_asked_for() -> None:
    """`as_of_ns` is the caller's event time; there is no default for it. A
    module that filled one in would be reading a clock (ADR-012)."""
    service = BookService()
    service.on_snapshot(snapshot(100, at_ns=BASE_NS))

    assert service.health().stale_ns == 0


@pytest.mark.trace("REQ-WP-004")
def test_the_same_stream_twice_gives_the_same_book_and_the_same_health() -> None:
    """SC-007. The property a clock would break, checked rather than assumed."""
    stream = [
        snapshot(100, bids=[("100", "9")], asks=[("101", "4")]),
        delta(101, 101, bids=[("99", "5")]),
        delta(102, 102, asks=[("102", "3")]),
        delta(110, 110),
        snapshot(200, bids=[("100", "1")], asks=[("101", "1")]),
        delta(201, 201, bids=[("99", "2")]),
    ]

    def run() -> tuple[dict, dict, tuple]:
        service = BookService()
        for event in stream:
            if isinstance(event, BookSnapshot):
                service.on_snapshot(event)
            else:
                service.on_delta(event)
        health = service.health(as_of_ns=BASE_NS + 500 * SECOND_NS)
        assert service.book is not None
        return (
            dict(service.book.bids),
            dict(service.book.asks),
            (health.valid, health.gap_count, health.last_sequence, health.stale_ns),
        )

    assert run() == run()


@pytest.mark.trace("REQ-WP-004")
def test_the_book_package_cannot_consult_a_clock() -> None:
    """SC-006, FR-010. Asserted over the source, as the bar builder and the
    backtest already are.

    A book whose staleness came from `time.time()` would report different
    health replaying the same recorded stream twice -- and the difference
    would look like a data problem.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "book"
    modules = list(package.glob("*.py"))
    assert modules, "the book package has no modules; this test would pass vacuously"
    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
