"""A minute of a book, finalised in event time (REQ-WP-095, spec 147).

Every expected number is arithmetic done by hand. The rules pinned: a minute is finalised from the
state of the book BEFORE the first message of the next minute (Principle I); OFI is the existing
tracker's, differenced over 1 Hz observations; a minute with no frame is stored with a count of zero
and no value (a thin minute is not a balanced one); a reconnect or a sequence gap breaks the OFI
baseline.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.context.minute_book import MinuteBook, MinuteSummary
from channelflow.domain import BookDelta, BookSnapshot, EventMeta, PriceLevel

SECOND = 1_000_000_000
MINUTE = 60 * SECOND
T0 = 1_791_699_960 * SECOND  # a whole minute


def meta(at: int, sequence: int | None = None) -> EventMeta:
    return EventMeta(
        source="test",
        venue="bybit",
        market_type="perp",
        symbol="BTCUSDT",
        event_time_ns=at,
        ingest_time_ns=at,
        sequence=sequence,
        source_event_id=None,
    )


def levels(rows: list[tuple[str, str]]) -> tuple[PriceLevel, ...]:
    return tuple(PriceLevel(price=Decimal(p), qty=Decimal(q)) for p, q in rows)


def book(
    at: int, bids: list[tuple[str, str]], asks: list[tuple[str, str]], update_id: int = 1
) -> BookSnapshot:
    return BookSnapshot(
        meta=meta(at, update_id), update_id=update_id, bids=levels(bids), asks=levels(asks)
    )


def ladder(
    best_bid: int, bid_qty: str, best_ask: int, ask_qty: str, depth: int = 10
) -> tuple[list, list]:
    """`depth` levels a side: the touch carries the given quantity, the rest 1 each."""
    bids = [(str(best_bid - i), bid_qty if i == 0 else "1") for i in range(depth)]
    asks = [(str(best_ask + i), ask_qty if i == 0 else "1") for i in range(depth)]
    return bids, asks


def snapshot_at(
    at: int,
    best_bid: int = 100,
    bid_qty: str = "5",
    best_ask: int = 101,
    ask_qty: str = "3",
    depth: int = 10,
    update_id: int = 1,
) -> BookSnapshot:
    bids, asks = ladder(best_bid, bid_qty, best_ask, ask_qty, depth)
    return book(at, bids, asks, update_id)


def delta(
    at: int,
    *,
    bids: list[tuple[str, str]] = (),
    asks: list[tuple[str, str]] = (),
    update_id: int,
    prev: int | None = None,
) -> BookDelta:  # type: ignore[assignment]
    return BookDelta(
        meta=meta(at, update_id),
        first_update_id=update_id,
        final_update_id=update_id,
        prev_update_id=update_id - 1 if prev is None else prev,
        bids=levels(list(bids)),
        asks=levels(list(asks)),
    )


def feed_seconds(
    mb: MinuteBook, start: int, seconds: int, *, first_id: int = 2
) -> list[MinuteSummary]:
    """A no-change delta every second: keeps the book alive and gives the tracker its samples."""
    out: list[MinuteSummary] = []
    for k in range(seconds):
        out += mb.feed(delta(start + (k + 1) * SECOND, update_id=first_id + k))
    return out


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_is_finalised_by_the_first_message_of_the_next_one() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    assert mb.feed(snapshot_at(T0 + 1 * SECOND)) == []
    done = feed_seconds(mb, T0 + 1 * SECOND, 58)  # up to T0 + 59 s: still inside the minute
    assert done == []

    (summary,) = mb.feed(delta(T0 + MINUTE + 1 * SECOND, update_id=60))

    assert summary.minute_close_ns == T0 + MINUTE
    assert (summary.bid, summary.ask, summary.mid) == (Decimal(100), Decimal(101), Decimal("100.5"))
    assert summary.observations > 0 and summary.frames > 0
    assert summary.quote_time_ns == T0 + 59 * SECOND  # the venue's time of the last message


@pytest.mark.trace("REQ-WP-095")
def test_the_summary_is_the_book_before_the_message_that_closed_the_minute() -> None:
    """The closing message already belongs to the next minute: it must not be in this one."""
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))
    feed_seconds(mb, T0 + SECOND, 5)
    moved = delta(
        T0 + MINUTE + 2 * SECOND,
        bids=[("100", "0"), ("109", "7")],  # the bid jumps to 109
        update_id=999,
        prev=6,
    )

    (summary,) = mb.feed(moved)

    assert summary.bid == Decimal(100)  # not 109


@pytest.mark.trace("REQ-WP-095")
def test_depth_imbalance_is_the_hand_computed_ten_level_ratio() -> None:
    # bids: 5 + 9*1 = 14 ; asks: 3 + 9*1 = 12 ; (14 - 12) / (14 + 12) = 2/26
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND, bid_qty="5", ask_qty="3"))
    feed_seconds(mb, T0 + SECOND, 5)

    (summary,) = mb.feed(delta(T0 + MINUTE + SECOND, update_id=500, prev=6))

    assert summary.depth_imbalance_10 == pytest.approx(2 / 26)


@pytest.mark.trace("REQ-WP-095")
def test_a_book_with_fewer_than_ten_levels_a_side_has_no_ten_level_imbalance() -> None:
    mb = MinuteBook(venue="okx", symbol="BTC-USDT-SWAP")
    mb.feed(snapshot_at(T0 + SECOND, depth=5))
    feed_seconds(mb, T0 + SECOND, 5)

    (summary,) = mb.feed(delta(T0 + MINUTE + SECOND, update_id=500, prev=6))

    assert summary.depth_imbalance_10 is None  # five levels are not ten under a ten-level name
    assert summary.mid is not None  # the quote is still real


@pytest.mark.trace("REQ-WP-095")
def test_ofi_over_the_minute_is_the_sum_of_the_second_by_second_increments() -> None:
    """Bid 100 @5 -> 100 @8 (+3 bid added); ask 101 @3 -> 101 @3: increment = +3."""
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + 0, bid_qty="5", ask_qty="3"))
    # first sample at the one-second grid after the snapshot: baseline, no increment yet
    mb.feed(delta(T0 + 1 * SECOND, update_id=2))
    mb.feed(delta(T0 + 2 * SECOND, bids=[("100", "8")], update_id=3))  # sampled next second
    mb.feed(delta(T0 + 3 * SECOND, update_id=4))
    mb.feed(delta(T0 + 4 * SECOND, update_id=5))

    (summary,) = mb.feed(delta(T0 + MINUTE + SECOND, update_id=6))

    assert summary.ofi == Decimal(3)
    assert summary.observations >= 3


@pytest.mark.trace("REQ-WP-095")
def test_a_silent_minute_is_finalised_by_the_clock_with_a_zero_count_and_no_values() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))

    (summary,) = mb.tick(now_ns=T0 + MINUTE + 5 * SECOND)

    assert summary.minute_close_ns == T0 + MINUTE
    assert summary.frames == 1
    assert summary.observations == 0 and summary.ofi is None


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_with_no_frame_at_all_has_a_count_of_zero_and_nothing_else() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))
    mb.tick(now_ns=T0 + MINUTE + 6 * SECOND)  # minute 1 closed

    (empty,) = mb.tick(now_ns=T0 + 2 * MINUTE + 6 * SECOND)

    assert empty.minute_close_ns == T0 + 2 * MINUTE
    assert (empty.frames, empty.observations) == (0, 0)
    assert empty.ofi is None and empty.depth_imbalance_10 is None and empty.mid is None


@pytest.mark.trace("REQ-WP-095")
def test_the_tick_does_nothing_before_the_minute_has_ended() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))
    assert mb.tick(now_ns=T0 + 30 * SECOND) == []


@pytest.mark.trace("REQ-WP-095")
def test_a_reset_breaks_the_ofi_baseline_so_no_increment_spans_the_gap() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND, bid_qty="5"))
    mb.feed(delta(T0 + 2 * SECOND, update_id=2))
    mb.reset()  # a reconnect: the book may have moved arbitrarily meanwhile
    mb.feed(snapshot_at(T0 + 30 * SECOND, bid_qty="500", ask_qty="1"))  # a very different book
    mb.feed(delta(T0 + 31 * SECOND, update_id=2))

    (summary,) = mb.feed(delta(T0 + MINUTE + SECOND, update_id=3))

    # the jump from the old book to the new one is not an order-flow increment
    assert summary.ofi is not None and abs(summary.ofi) < 400


@pytest.mark.trace("REQ-WP-095")
def test_a_sequence_gap_asks_for_a_resync_and_breaks_the_baseline() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))
    mb.feed(delta(T0 + 2 * SECOND, update_id=2))
    assert not mb.needs_resync

    mb.feed(delta(T0 + 3 * SECOND, update_id=9, prev=8))  # 3..8 never seen

    assert mb.needs_resync


@pytest.mark.trace("REQ-WP-095")
def test_a_resync_snapshot_clears_the_request() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))
    mb.feed(delta(T0 + 2 * SECOND, update_id=9, prev=8))
    assert mb.needs_resync

    mb.feed(snapshot_at(T0 + 3 * SECOND, update_id=20))

    assert not mb.needs_resync


@pytest.mark.trace("REQ-WP-095")
def test_a_crossed_book_is_refused_and_does_not_become_a_quote() -> None:
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + SECOND))
    feed_seconds(mb, T0 + SECOND, 3)
    crossed = delta(
        T0 + 5 * SECOND, bids=[("102", "4")], update_id=5
    )  # bid above the 101 ask, in sequence
    mb.feed(crossed)
    assert not mb.needs_resync  # it is a valid book that is crossed, not a broken one

    (summary,) = mb.feed(delta(T0 + MINUTE + SECOND, update_id=6))

    assert summary.mid is None and summary.bid is None and summary.ask is None


@pytest.mark.trace("REQ-WP-095")
def test_each_minutes_ofi_is_its_own_and_not_a_running_total() -> None:
    """Minute 1 has one +3 increment, minute 2 none: the second must not carry the first's."""
    mb = MinuteBook(venue="bybit", symbol="BTCUSDT")
    mb.feed(snapshot_at(T0 + 0, bid_qty="5", ask_qty="3"))
    mb.feed(delta(T0 + 1 * SECOND, update_id=2))
    mb.feed(delta(T0 + 2 * SECOND, bids=[("100", "8")], update_id=3))  # the bid grows by 3
    mb.feed(delta(T0 + 3 * SECOND, update_id=4))
    (first,) = mb.feed(delta(T0 + MINUTE + 1 * SECOND, update_id=5))
    for k in range(2, 6):
        mb.feed(delta(T0 + MINUTE + k * SECOND, update_id=4 + k))
    (second,) = mb.feed(delta(T0 + 2 * MINUTE + 1 * SECOND, update_id=20))

    assert first.ofi == Decimal(3)
    assert second.ofi == Decimal(0)  # a real measurement of a book that did not move
