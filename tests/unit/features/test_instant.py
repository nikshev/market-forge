"""Queue imbalance, depth imbalance and microprice (REQ-WP-011).

PRD sections 15.1 and 15.2. Pure functions of one book state: no windows, no
history, nothing to accumulate wrongly.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.book import BookInvalid, BookService
from channelflow.features import instant

from .conftest import book_of, gapping_delta

#: bids 100.40 x 1, 100.30 x 2, 100.00 x 4, 99.00 x 8   (total 15)
#: asks 100.60 x 1, 100.70 x 2, 101.00 x 4, 102.00 x 8  (total 15)
#: mid = 100.50
DEEP_BIDS = [("100.40", "1"), ("100.30", "2"), ("100.00", "4"), ("99.00", "8")]
DEEP_ASKS = [("100.60", "1"), ("100.70", "2"), ("101.00", "4"), ("102.00", "8")]


@pytest.mark.trace("REQ-WP-011")
def test_queue_imbalance_at_the_touch(lopsided: BookService) -> None:
    """FR-001, SC-001. (2 - 6) / (2 + 6) = -0.5."""
    assert instant.queue_imbalance(lopsided) == pytest.approx(-0.5)


@pytest.mark.trace("REQ-WP-011")
def test_queue_imbalance_is_zero_when_the_queues_match(balanced: BookService) -> None:
    assert instant.queue_imbalance(balanced) == pytest.approx(0.0)


@pytest.mark.trace("REQ-WP-011")
@pytest.mark.parametrize(
    ("levels_deep", "expected"),
    [
        # bid side cumulative: 1, 3, 7, 15 -- ask side identical, so every
        # symmetric depth is balanced. The asymmetry is introduced below.
        (1, 0.0),
        (2, 0.0),
        (4, 0.0),
    ],
)
def test_depth_imbalance_over_a_symmetric_book_is_zero(levels_deep: int, expected: float) -> None:
    """FR-002. A book that is a mirror of itself has no imbalance at any depth."""
    book = book_of(DEEP_BIDS, DEEP_ASKS)
    assert instant.depth_imbalance_levels(book, levels_deep) == pytest.approx(expected)


@pytest.mark.trace("REQ-WP-011")
def test_depth_imbalance_deepens_as_more_levels_are_counted() -> None:
    """FR-002, SC-001, hand-computed.

    bids 100.40 x 1, 100.30 x 1   asks 100.60 x 1, 100.70 x 9
      top 1: (1 - 1) / 2  =  0.0
      top 2: (2 - 10) / 12 = -0.666...
    A single-depth test would pass a function that ignored its `n`.
    """
    book = book_of([("100.40", "1"), ("100.30", "1")], [("100.60", "1"), ("100.70", "9")])

    assert instant.depth_imbalance_levels(book, 1) == pytest.approx(0.0)
    assert instant.depth_imbalance_levels(book, 2) == pytest.approx(-8 / 12)


@pytest.mark.trace("REQ-WP-011")
def test_depth_imbalance_over_basis_point_bands() -> None:
    """FR-003, SC-001. Bands are measured from the mid -- ADR-011.

    mid = 100.50, so one bp is 0.010050.
      10 bps -> +/-0.1005 -> bids >= 100.3995 (1), asks <= 100.6005 (1) -> 0.0
      20 bps -> +/-0.2010 -> bids >= 100.2990 (1+2=3), asks <= 100.7010 (1+2=3) -> 0.0
      50 bps -> +/-0.5025 -> bids >= 99.9975  (7),      asks <= 101.0025 (7)     -> 0.0
    """
    book = book_of(DEEP_BIDS, DEEP_ASKS)

    for bps in (10, 20, 50):
        assert instant.depth_imbalance_bps(book, bps) == pytest.approx(0.0)


@pytest.mark.trace("REQ-WP-011")
def test_a_band_imbalance_reflects_lopsided_depth() -> None:
    """The asymmetric case, so the previous test's zeros are not the only proof.

    bids 100.40 x 1, asks 100.60 x 1 and 100.70 x 9; mid = 100.50.
      10 bps -> bids 1, asks 1                 ->  0.0
      20 bps -> bids 1, asks 10                -> (1-10)/11 = -0.8181...
    """
    book = book_of([("100.40", "1")], [("100.60", "1"), ("100.70", "9")])

    assert instant.depth_imbalance_bps(book, 10) == pytest.approx(0.0)
    assert instant.depth_imbalance_bps(book, 20) == pytest.approx(-9 / 11)


@pytest.mark.trace("REQ-WP-011")
def test_the_microprice_leans_away_from_the_larger_queue(lopsided: BookService) -> None:
    """FR-004, SC-002. (100*6 + 101*2) / 8 = 100.25, below the 100.50 mid.

    The weighting is by the *opposite* queue: a big ask queue is sellers
    waiting, and the price they will actually get is nearer the bid.
    """
    assert instant.microprice(lopsided) == Decimal("100.25")
    assert instant.microprice(lopsided) < lopsided.mid()


@pytest.mark.trace("REQ-WP-011")
def test_the_microprice_equals_the_mid_when_the_queues_match(
    balanced: BookService,
) -> None:
    """SC-002. The one case where the answer is forced, so it pins the weighting
    direction: a formula weighting by the *same* side gives the mid here too,
    which is why the lopsided case above is the real test."""
    assert instant.microprice(balanced) == balanced.mid()


@pytest.mark.trace("REQ-WP-011")
def test_the_microprice_mid_spread_is_reported_in_basis_points(
    lopsided: BookService,
) -> None:
    """FR-004. (100.25 - 100.50) / 100.50 * 10_000 = -24.87562... bps."""
    assert instant.microprice_mid_spread_bps(lopsided) == pytest.approx(-24.875621890547265)


@pytest.mark.trace("REQ-WP-011")
def test_every_instant_feature_refuses_an_invalid_book() -> None:
    """FR-005, SC-009, PRD section 11.1 rule 6.

    Listed one by one rather than trusted to a shared guard: a feature added
    later that reads the book directly is exactly what this must catch.
    """
    service = book_of([("100", "2")], [("101", "6")])
    service.on_delta(gapping_delta())
    assert not service.health().valid, "the fixture must actually break the book"

    for name, call in (
        ("queue_imbalance", lambda: instant.queue_imbalance(service)),
        ("depth_imbalance_levels", lambda: instant.depth_imbalance_levels(service, 5)),
        ("depth_imbalance_bps", lambda: instant.depth_imbalance_bps(service, 10)),
        ("microprice", lambda: instant.microprice(service)),
        ("microprice_mid_spread_bps", lambda: instant.microprice_mid_spread_bps(service)),
    ):
        with pytest.raises(BookInvalid):
            call()
            pytest.fail(f"{name} answered from a book that has diverged")


@pytest.mark.trace("REQ-WP-011")
def test_queue_imbalance_refuses_an_empty_side() -> None:
    """The spec's first edge case: no opposite queue, no imbalance."""
    book = book_of([("100", "2")], [])

    with pytest.raises(BookInvalid):
        instant.queue_imbalance(book)


@pytest.mark.trace("REQ-WP-011")
def test_queue_imbalance_refuses_two_zero_sized_touches() -> None:
    """The spec's second edge case: the denominator is zero, and a book with
    two empty touches carries no imbalance information to report."""
    book = book_of([("100", "0")], [("101", "0")])

    with pytest.raises(BookInvalid):
        instant.queue_imbalance(book)
