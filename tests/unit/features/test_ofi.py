"""Order flow imbalance (REQ-WP-011).

PRD section 15.3 asks for Cont-style top-of-book OFI. The increment between two
consecutive observations is:

    e = 1[Pb_n >= Pb_{n-1}] * Qb_n  -  1[Pb_n <= Pb_{n-1}] * Qb_{n-1}
      - 1[Pa_n <= Pa_{n-1}] * Qa_n  +  1[Pa_n >= Pa_{n-1}] * Qa_{n-1}

When a price is unchanged both indicators fire, and the term collapses to the
*change* in size. That collapse is the part worth testing directly: an
implementation that only handled the moving-price cases would look right on
half the data.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.features.ofi import Observation, OFITracker

from .conftest import BASE_NS, SECOND_NS


def obs(bid: str, bid_qty: str, ask: str, ask_qty: str, *, at_ns: int) -> Observation:
    return Observation(
        bid_price=Decimal(bid),
        bid_qty=Decimal(bid_qty),
        ask_price=Decimal(ask),
        ask_qty=Decimal(ask_qty),
        event_time_ns=at_ns,
    )


@pytest.mark.trace("REQ-WP-011")
def test_the_first_observation_produces_no_increment() -> None:
    """There is nothing to difference against. A tracker that emitted the first
    reading as an increment would count the standing book as flow."""
    tracker = OFITracker()
    assert tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS)) is None


@pytest.mark.trace("REQ-WP-011")
def test_an_unchanged_bid_price_contributes_the_size_change() -> None:
    """SC-003, the collapse case. Bid stays at 100, size 5 -> 8: +3.
    Ask stays at 101, size 5 -> 5: 0. Increment = +3."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))

    assert tracker.observe(obs("100", "8", "101", "5", at_ns=BASE_NS + 1)) == Decimal(3)


@pytest.mark.trace("REQ-WP-011")
def test_a_rising_bid_price_contributes_its_whole_new_size() -> None:
    """Bid 100 -> 100.5: the old queue is gone and the new one is demand.
    Qb_n = 4, and the old size is not subtracted because Pb_n > Pb_{n-1}."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))

    assert tracker.observe(obs("100.5", "4", "101", "5", at_ns=BASE_NS + 1)) == Decimal(4)


@pytest.mark.trace("REQ-WP-011")
def test_a_falling_bid_price_removes_the_old_size() -> None:
    """Bid 100 -> 99.5: the old bid queue was pulled or eaten. -Qb_{n-1} = -5."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))

    assert tracker.observe(obs("99.5", "4", "101", "5", at_ns=BASE_NS + 1)) == Decimal(-5)


@pytest.mark.trace("REQ-WP-011")
def test_the_ask_side_enters_with_the_opposite_sign() -> None:
    """A falling ask is supply pressing down: -Qa_n. Ask 101 -> 100.5, size 7,
    with the bid unchanged and unchanged in size."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))

    assert tracker.observe(obs("100", "5", "100.5", "7", at_ns=BASE_NS + 1)) == Decimal(-7)


@pytest.mark.trace("REQ-WP-011")
def test_a_rising_ask_price_adds_back_the_old_size() -> None:
    """Ask 101 -> 101.5: the supply that was resting there is gone. +Qa_{n-1}."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))

    assert tracker.observe(obs("100", "5", "101.5", "9", at_ns=BASE_NS + 1)) == Decimal(5)


@pytest.mark.trace("REQ-WP-011")
def test_both_sides_combine_in_one_increment() -> None:
    """Bid 100 x 5 -> 100 x 9 (+4); ask 101 x 5 -> 101 x 2 (-(2-5) = +3).
    Total +7. A test of one side at a time would miss a sign error in the sum.
    """
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))

    assert tracker.observe(obs("100", "9", "101", "2", at_ns=BASE_NS + 1)) == Decimal(7)


@pytest.mark.trace("REQ-WP-011")
def test_a_window_sums_the_increments_inside_it() -> None:
    """SC-003, FR-007.

    Two increments of +3 early, a third five seconds later. A one-second window
    at the end sees only the third; a ten-second window sees all three. Both
    directions matter: a window that ignored its length would pass the first
    assertion, and one that dropped everything old would pass the second.
    """
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))
    tracker.observe(obs("100", "8", "101", "5", at_ns=BASE_NS + 1))
    tracker.observe(obs("100", "11", "101", "5", at_ns=BASE_NS + 2))
    tracker.observe(obs("100", "14", "101", "5", at_ns=BASE_NS + 5 * SECOND_NS))

    recent = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 5 * SECOND_NS)
    assert recent.value == Decimal(3)
    assert recent.observations == 1

    everything = tracker.window(10 * SECOND_NS, as_of_ns=BASE_NS + 5 * SECOND_NS)
    assert everything.value == Decimal(9)
    assert everything.observations == 3


@pytest.mark.trace("REQ-WP-011")
def test_an_empty_window_is_distinguishable_from_a_balanced_one() -> None:
    """FR-008, SC-003. Zero flow and no observations both read as 0; only the
    count says which happened, and a caller acting on 'balanced' when the feed
    was simply silent is acting on nothing."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))
    tracker.observe(obs("100", "8", "101", "5", at_ns=BASE_NS + 1))

    silent = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 60 * SECOND_NS)
    assert silent.value == Decimal(0)
    assert silent.observations == 0
    assert silent.is_empty

    active = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 1)
    assert active.observations == 1
    assert not active.is_empty


@pytest.mark.trace("REQ-WP-011")
def test_no_increment_is_computed_across_a_gap() -> None:
    """SC-004, FR-009. The load-bearing one.

    Two book states either side of a sequence gap are not consecutive.
    Differencing them attributes every change during the outage to a single
    instant of flow -- a number that looks entirely ordinary and describes
    something nobody observed.
    """
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS))
    tracker.on_discontinuity()

    assert tracker.observe(obs("100", "500", "101", "5", at_ns=BASE_NS + 1)) is None
    assert tracker.window(SECOND_NS, as_of_ns=BASE_NS + 1).value == Decimal(0)

    # ...and the observation after the discontinuity becomes the new baseline.
    assert tracker.observe(obs("100", "503", "101", "5", at_ns=BASE_NS + 2)) == Decimal(3)


@pytest.mark.trace("REQ-WP-011")
def test_observations_must_arrive_in_event_time_order() -> None:
    """An out-of-order observation would difference against the future."""
    tracker = OFITracker()
    tracker.observe(obs("100", "5", "101", "5", at_ns=BASE_NS + SECOND_NS))

    with pytest.raises(ValueError, match="event-time order"):
        tracker.observe(obs("100", "8", "101", "5", at_ns=BASE_NS))


@pytest.mark.trace("REQ-WP-011")
def test_every_prd_window_length_is_available() -> None:
    """FR-007: 1s, 5s, 30s, 1m and one bar."""
    from channelflow.features.ofi import WINDOWS

    assert WINDOWS == (SECOND_NS, 5 * SECOND_NS, 30 * SECOND_NS, 60 * SECOND_NS)
