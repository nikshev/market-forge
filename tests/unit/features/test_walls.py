"""The lifecycle of a resting wall (REQ-WP-011).

PRD section 15.6 gives the state: side, price band, first and last seen, max
and average size, executed and cancelled estimates, refill and move counts,
persistence.

The estimates are the point. PRD section 2.2 warns that large passive orders
can vanish quickly, so a static heatmap creates a false sense of liquidity: a
wall that was eaten and a wall that was pulled tell opposite stories about the
same picture. ADR-014's rule is `executed = min(decrease, traded at that price)`
and the rest is cancellation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.features.walls import WallTracker

from .conftest import BASE_NS, SECOND_NS, book_of, trade

#: A 40-unit bid against neighbours of 1 and 2: unmistakably anomalous.
WALL_BOOK = [("100", "40"), ("99.9", "1"), ("99.8", "2")]
ASKS = [("101", "1"), ("101.1", "2")]


def _at(size: str, *, at_ns: int):
    return book_of([("100", size), ("99.9", "1"), ("99.8", "2")], ASKS, at_ns=at_ns)


@pytest.mark.trace("REQ-WP-011")
def test_a_level_far_larger_than_its_neighbours_becomes_a_wall() -> None:
    """FR-013, SC-006."""
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)

    walls = tracker.active
    assert len(walls) == 1
    wall = walls[0]
    assert wall.side == "bid"
    assert wall.price == Decimal("100")
    assert wall.first_seen_ns == BASE_NS
    assert wall.max_size == Decimal("40")


@pytest.mark.trace("REQ-WP-011")
def test_an_ordinary_level_is_not_a_wall() -> None:
    """Guard on the detector: if everything is a wall, nothing is.

    Three levels of similar size have no anomaly to find, and a detector that
    tracked them all would make every later assertion meaningless.
    """
    tracker = WallTracker()
    tracker.observe(
        book_of([("100", "3"), ("99.9", "2"), ("99.8", "2")], ASKS, at_ns=BASE_NS),
        trades=(),
        as_of_ns=BASE_NS,
    )

    assert tracker.active == ()


@pytest.mark.trace("REQ-WP-011")
def test_a_decrease_matched_by_trades_is_recorded_as_executed() -> None:
    """FR-015, SC-006, ADR-014. 40 -> 25 is a decrease of 15, and 15 traded at
    100 in the interval: all of it executed, none cancelled."""
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(
        _at("25", at_ns=BASE_NS + SECOND_NS),
        trades=(trade("t1", "100", "15", "sell", at_ns=BASE_NS + SECOND_NS),),
        as_of_ns=BASE_NS + SECOND_NS,
    )

    wall = tracker.active[0]
    assert wall.executed_size_est == Decimal("15")
    assert wall.cancelled_size_est == Decimal("0")


@pytest.mark.trace("REQ-WP-011")
def test_a_decrease_with_no_trades_is_recorded_as_cancelled() -> None:
    """FR-015, ADR-014. The tape is the evidence; the book alone cannot say why
    size left. Nothing traded, so nothing was executed."""
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(_at("25", at_ns=BASE_NS + SECOND_NS), trades=(), as_of_ns=BASE_NS + SECOND_NS)

    wall = tracker.active[0]
    assert wall.executed_size_est == Decimal("0")
    assert wall.cancelled_size_est == Decimal("15")


@pytest.mark.trace("REQ-WP-011")
def test_executed_never_exceeds_what_actually_traded_there() -> None:
    """SC-006, ADR-014's bound, and the mutation T011 targets.

    40 -> 10 is a decrease of 30; only 4 traded at that price. The other 26 were
    pulled. An implementation attributing the whole decrease to execution would
    report a wall that was abandoned as one that was absorbed -- believable
    output describing the opposite of what happened.
    """
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(
        _at("10", at_ns=BASE_NS + SECOND_NS),
        trades=(trade("t1", "100", "4", "sell", at_ns=BASE_NS + SECOND_NS),),
        as_of_ns=BASE_NS + SECOND_NS,
    )

    wall = tracker.active[0]
    assert wall.executed_size_est == Decimal("4")
    assert wall.cancelled_size_est == Decimal("26")


@pytest.mark.trace("REQ-WP-011")
def test_trades_at_another_price_are_not_attributed_to_this_wall() -> None:
    """ADR-014: trades are attributed to the price they printed at, not a band.
    A trade at 99.9 says nothing about the 100 level's decrease."""
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(
        _at("25", at_ns=BASE_NS + SECOND_NS),
        trades=(trade("t1", "99.9", "15", "sell", at_ns=BASE_NS + SECOND_NS),),
        as_of_ns=BASE_NS + SECOND_NS,
    )

    assert tracker.active[0].cancelled_size_est == Decimal("15")


@pytest.mark.trace("REQ-WP-011")
def test_a_wall_that_grows_again_is_a_refill_not_a_new_wall() -> None:
    """FR-014, SC-006. Refills are the behaviour section 15.6 scores; treating
    each one as a fresh wall would erase the persistence it is scoring."""
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(_at("25", at_ns=BASE_NS + SECOND_NS), trades=(), as_of_ns=BASE_NS + SECOND_NS)
    tracker.observe(
        _at("45", at_ns=BASE_NS + 2 * SECOND_NS), trades=(), as_of_ns=BASE_NS + 2 * SECOND_NS
    )

    walls = tracker.active
    assert len(walls) == 1
    assert walls[0].refill_count == 1
    assert walls[0].first_seen_ns == BASE_NS, "the wall is the same one"
    assert walls[0].max_size == Decimal("45")


@pytest.mark.trace("REQ-WP-011")
def test_persistence_is_measured_in_event_time() -> None:
    """FR-014, FR-019. Three seconds of book time is three seconds of
    persistence however long the replay took."""
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(
        _at("40", at_ns=BASE_NS + 3 * SECOND_NS), trades=(), as_of_ns=BASE_NS + 3 * SECOND_NS
    )

    assert tracker.active[0].persistence_ns == 3 * SECOND_NS


@pytest.mark.trace("REQ-WP-011")
def test_a_finished_wall_is_kept_and_never_rewritten() -> None:
    """FR-016, SC-006, Principle III.

    The wall is gone from the book; what it did is not undone by that.
    """
    tracker = WallTracker()
    tracker.observe(book_of(WALL_BOOK, ASKS, at_ns=BASE_NS), trades=(), as_of_ns=BASE_NS)
    tracker.observe(
        book_of([("99.9", "1"), ("99.8", "2")], ASKS, at_ns=BASE_NS + SECOND_NS),
        trades=(),
        as_of_ns=BASE_NS + SECOND_NS,
    )

    assert tracker.active == ()
    assert len(tracker.finished) == 1
    finished = tracker.finished[0]
    assert finished.last_seen_ns == BASE_NS + SECOND_NS
    assert finished.cancelled_size_est == Decimal("40")

    with pytest.raises(Exception):  # noqa: B017 -- frozen model
        finished.max_size = Decimal("1")  # type: ignore[misc]


@pytest.mark.trace("REQ-WP-011")
def test_the_anomaly_threshold_is_configurable() -> None:
    """Principle X, and PRD section 13.11's warning that research defaults are
    not proven parameters. A 3x wall is a wall at threshold 2 and not at 10.

    The ask side here is deliberately flat. With the two-level `ASKS` the other
    tests use, its far level is twice its near one -- itself an anomaly at a
    threshold of 2, and the test would be counting it.
    """
    flat_asks = [("101", "2"), ("101.1", "2"), ("101.2", "2")]
    book = book_of([("100", "6"), ("99.9", "2"), ("99.8", "2")], flat_asks, at_ns=BASE_NS)

    lenient = WallTracker(size_multiple=2.0)
    lenient.observe(book, trades=(), as_of_ns=BASE_NS)
    assert [(w.side, w.price) for w in lenient.active] == [("bid", Decimal("100"))]

    strict = WallTracker(size_multiple=10.0)
    strict.observe(book, trades=(), as_of_ns=BASE_NS)
    assert strict.active == ()
