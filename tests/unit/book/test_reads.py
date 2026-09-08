"""Top-N and depth-at-bps (REQ-WP-004).

PRD section 15.1 names the bands -- +/-5/10/25/50 bps -- and section 15.5 asks
for depth within X bps, without ever saying from what. ADR-011 settles it: the
mid price, the same reference for both sides, because section 15.1's `DI_k` is
a bid/ask depth ratio and two sides measured from different references are not
comparable.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.book import BookInvalid, BookService

from .conftest import snapshot

#: mid = 100.5. A basis point is 0.01005, so:
#:   10 bps -> 0.1005 -> bids at 100.40 and above, asks at 100.60 and below
#:   50 bps -> 0.5025 -> bids at 100.00 and above, asks at 101.00 and below
BOOK = {
    "bids": [("100.40", "1"), ("100.30", "2"), ("100.00", "4"), ("99.00", "8")],
    "asks": [("100.60", "1"), ("100.70", "2"), ("101.00", "4"), ("102.00", "8")],
}


def _service() -> BookService:
    service = BookService()
    service.on_snapshot(snapshot(100, bids=BOOK["bids"], asks=BOOK["asks"]))
    return service


@pytest.mark.trace("REQ-WP-004")
def test_top_n_is_ordered_from_the_touch_outward() -> None:
    """FR-007. Bids descend, asks ascend: both start at the best price."""
    bids, asks = _service().top(3)

    assert [level.price for level in bids] == [
        Decimal("100.40"),
        Decimal("100.30"),
        Decimal("100.00"),
    ]
    assert [level.price for level in asks] == [
        Decimal("100.60"),
        Decimal("100.70"),
        Decimal("101.00"),
    ]
    assert [level.qty for level in bids] == [Decimal("1"), Decimal("2"), Decimal("4")]


@pytest.mark.trace("REQ-WP-004")
def test_a_short_side_returns_what_exists() -> None:
    """The spec's third US3 scenario: no padding, no error."""
    service = BookService()
    service.on_snapshot(snapshot(100, bids=[("100", "1")], asks=[("101", "1"), ("102", "2")]))

    bids, asks = service.top(10)

    assert len(bids) == 1
    assert len(asks) == 2


@pytest.mark.trace("REQ-WP-004")
def test_depth_within_bps_counts_from_the_mid() -> None:
    """SC-004, ADR-011. Hand-computed against the book above."""
    service = _service()

    assert service.depth_within_bps(10) == (Decimal("1"), Decimal("1"))
    assert service.depth_within_bps(20) == (Decimal("3"), Decimal("3"))
    assert service.depth_within_bps(50) == (Decimal("7"), Decimal("7"))
    assert service.depth_within_bps(200) == (Decimal("15"), Decimal("15"))


@pytest.mark.trace("REQ-WP-004")
def test_depth_is_measured_from_the_mid_and_not_from_each_side() -> None:
    """The distinction ADR-011 turns on, made observable.

    A wide spread with liquidity stacked on one side: measured from the mid,
    the near bid at 100 is 249 bps away and 10 bps includes nothing. Measured
    from each side's own best price it would be at distance zero and included.
    A test that only used a tight book would pass under either rule.
    """
    service = BookService()
    service.on_snapshot(snapshot(100, bids=[("100", "5"), ("99", "5")], asks=[("105", "5")]))

    assert service.depth_within_bps(10) == (Decimal("0"), Decimal("0")), (
        "measured from each side's own best price this would be 5 and 5"
    )
    assert service.depth_within_bps(300) == (Decimal("5"), Decimal("5"))


@pytest.mark.trace("REQ-WP-004")
def test_depth_refuses_when_one_side_is_empty() -> None:
    """The spec's fifth edge case: no mid, no reference, no answer."""
    service = BookService()
    service.on_snapshot(snapshot(100, bids=[("100", "1")], asks=[]))

    with pytest.raises(BookInvalid, match="mid"):
        service.depth_within_bps(10)


@pytest.mark.trace("REQ-WP-004")
def test_an_empty_side_has_zero_depth_when_a_mid_still_exists() -> None:
    """The spec's fourth edge case. Zero is a fact about the book, not an error
    -- distinct from the case above, where there is no reference to measure."""
    service = BookService()
    service.on_snapshot(snapshot(100, bids=[("100", "5")], asks=[("101", "5")]))

    assert service.depth_within_bps(1) == (Decimal("0"), Decimal("0"))
