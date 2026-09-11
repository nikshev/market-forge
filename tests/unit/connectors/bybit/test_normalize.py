"""Bybit v5 messages become the same canonical events (REQ-WP-043).

Every payload here is real traffic, recorded from the public venue. [[ADR-004]]:
a live message carries fields the documentation does not mention, and a
hand-written sample encodes the author's misunderstanding as a passing test.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from channelflow.connectors.bybit import (
    NormalizationError,
    order_book_message,
    public_trade,
    rest_order_book,
)
from channelflow.domain import BookDelta, BookSnapshot

VENUE = {"venue": "bybit", "market_type": "linear"}
INGEST = 1_789_000_000_000_000_000


# --- trades --------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-043")
def test_every_recorded_trade_normalises(trade_messages: list[dict[str, Any]]) -> None:
    for message in trade_messages:
        for raw in message["data"]:
            event = public_trade(raw, **VENUE, ingest_time_ns=INGEST)
            assert event.price > 0
            assert event.qty_base > 0
            assert event.meta.symbol == raw["s"]


@pytest.mark.trace("REQ-WP-043")
def test_the_side_is_the_taker_s_and_is_not_derived(
    trade_messages: list[dict[str, Any]],
) -> None:
    """Bybit's `S` is the taker side; Binance's `m` says the buyer was the
    maker. One canonical field, two conventions, and getting this backwards
    inverts every order-flow figure above it without a symptom.
    """
    for message in trade_messages:
        for raw in message["data"]:
            event = public_trade(raw, **VENUE, ingest_time_ns=INGEST)

            assert event.aggressor_side == ("buy" if raw["S"] == "Buy" else "sell")
            # The buyer was the maker exactly when the taker was the seller.
            assert event.is_buyer_maker is (raw["S"] == "Sell")


@pytest.mark.trace("REQ-WP-043")
def test_the_event_time_is_the_fill_and_not_the_push(
    trade_messages: list[dict[str, Any]],
) -> None:
    """`T` is when the order filled; the envelope's `ts` is when Bybit pushed
    the batch. The second measures venue-side latency and is not market
    information (PRD §9)."""
    message = trade_messages[0]
    raw = message["data"][0]

    event = public_trade(raw, **VENUE, ingest_time_ns=INGEST)

    assert event.meta.event_time_ns == raw["T"] * 1_000_000
    assert event.meta.ingest_time_ns == INGEST


@pytest.mark.trace("REQ-WP-043")
def test_a_price_that_float64_cannot_hold_survives(
    trade_messages: list[dict[str, Any]],
) -> None:
    raw = dict(trade_messages[0]["data"][0])
    raw["p"] = "78832.20000000000001"

    assert public_trade(raw, **VENUE, ingest_time_ns=INGEST).price == Decimal(
        "78832.20000000000001"
    )


@pytest.mark.trace("REQ-WP-043")
def test_an_unknown_side_is_refused(trade_messages: list[dict[str, Any]]) -> None:
    """Refused, not defaulted. A side this connector does not recognise is a
    venue change, and guessing one would put a number nobody checked into
    order-flow."""
    raw = dict(trade_messages[0]["data"][0])
    raw["S"] = "Unknown"

    with pytest.raises(NormalizationError, match="taker side"):
        public_trade(raw, **VENUE, ingest_time_ns=INGEST)


@pytest.mark.trace("REQ-WP-043")
def test_a_message_missing_a_field_is_refused(
    trade_messages: list[dict[str, Any]],
) -> None:
    """A connector that dropped what it could not read would report a quiet
    market, and a quiet market is a thing somebody trades on."""
    raw = dict(trade_messages[0]["data"][0])
    del raw["p"]

    with pytest.raises(NormalizationError):
        public_trade(raw, **VENUE, ingest_time_ns=INGEST)


# --- the order book ------------------------------------------------------------


@pytest.mark.trace("REQ-WP-043")
def test_the_first_message_is_a_snapshot_and_the_rest_are_deltas(
    book_messages: list[dict[str, Any]],
) -> None:
    events = [order_book_message(m, **VENUE, ingest_time_ns=INGEST) for m in book_messages]

    assert isinstance(events[0], BookSnapshot)
    assert all(isinstance(e, BookDelta) for e in events[1:])


@pytest.mark.trace("REQ-WP-043")
def test_the_update_id_is_what_increments_and_the_cross_sequence_is_not(
    book_messages: list[dict[str, Any]],
) -> None:
    """The finding that justifies recording fixtures rather than writing them.

    The orderbook documentation's prose says to watch `seq` for discontinuities;
    its own field table calls `seq` a cross sequence for comparing depth levels.
    Forty consecutive recorded messages settle it: `u` increments by exactly one
    every time, and `seq` jumps by between 34 and 289.

    A gap detector written from the prose would resubscribe constantly on a
    healthy stream.
    """
    ids = [m["data"]["u"] for m in book_messages]
    crosses = [m["data"]["seq"] for m in book_messages]

    assert {b - a for a, b in zip(ids, ids[1:], strict=False)} == {1}
    assert {b - a for a, b in zip(crosses, crosses[1:], strict=False)} != {1}


@pytest.mark.trace("REQ-WP-043")
def test_a_delta_names_one_update_and_its_predecessor(
    book_messages: list[dict[str, Any]],
) -> None:
    """Bybit sends one id per message rather than a range, so first and final
    are the same number. Said out loud because a reader who assumed a
    Binance-style range would look for a gap that cannot appear."""
    delta = order_book_message(book_messages[1], **VENUE, ingest_time_ns=INGEST)
    assert isinstance(delta, BookDelta)

    assert delta.first_update_id == delta.final_update_id
    assert delta.prev_update_id == delta.final_update_id - 1


@pytest.mark.trace("REQ-WP-043")
def test_the_book_s_event_time_is_the_matching_engine_s(
    book_messages: list[dict[str, Any]],
) -> None:
    """`cts` correlates with public trades; the envelope's `ts` is the push
    time. The first is market information and the second is not."""
    message = book_messages[0]

    event = order_book_message(message, **VENUE, ingest_time_ns=INGEST)

    assert event.meta.event_time_ns == message["cts"] * 1_000_000


@pytest.mark.trace("REQ-WP-043")
def test_the_recorded_stream_reconstructs_without_a_gap(
    book_messages: list[dict[str, Any]],
) -> None:
    """The whole point of the connector: the book layer consumes these without
    knowing which venue they came from."""
    from channelflow.book import OrderBook

    events = [order_book_message(m, **VENUE, ingest_time_ns=INGEST) for m in book_messages]
    book = OrderBook.from_snapshot(events[0])  # type: ignore[arg-type]
    for delta in events[1:]:
        book.apply(delta)  # type: ignore[arg-type]

    health = book.health()
    assert health.valid
    assert health.gap_count == 0


@pytest.mark.trace("REQ-WP-043")
def test_an_unknown_message_type_is_refused(
    book_messages: list[dict[str, Any]],
) -> None:
    message = dict(book_messages[0])
    message["type"] = "something_new"

    with pytest.raises(NormalizationError, match="unknown message type"):
        order_book_message(message, **VENUE, ingest_time_ns=INGEST)


# --- REST ----------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-043")
def test_the_rest_snapshot_has_its_own_event_time(rest_book: dict[str, Any]) -> None:
    """Unlike the Binance REST snapshot, this one carries the venue's timestamp,
    so it does not have to borrow receipt for both clocks."""
    snapshot = rest_order_book(rest_book, **VENUE, ingest_time_ns=INGEST)

    assert snapshot.meta.event_time_ns == rest_book["result"]["ts"] * 1_000_000
    assert snapshot.meta.event_time_ns != snapshot.meta.ingest_time_ns
    assert snapshot.bids and snapshot.asks


@pytest.mark.trace("REQ-WP-043")
def test_the_bids_are_the_bids(book_messages: list[dict[str, Any]]) -> None:
    """Swapping the two arrays produces a book that reconstructs cleanly, passes
    every sequencing test, and inverts the spread.

    Nothing above would raise: an order book with the best bid above the best
    ask is arithmetically fine and economically impossible, and every
    microstructure figure built on it would be wrong in a direction nobody
    could trace back to a connector.
    """
    snapshot = order_book_message(book_messages[0], **VENUE, ingest_time_ns=INGEST)
    assert isinstance(snapshot, BookSnapshot)

    best_bid = max(level.price for level in snapshot.bids)
    best_ask = min(level.price for level in snapshot.asks)

    assert best_bid < best_ask
    # And the venue's own order survives: `b` descends, `a` ascends.
    assert [level.price for level in snapshot.bids] == sorted(
        (level.price for level in snapshot.bids), reverse=True
    )
    assert [level.price for level in snapshot.asks] == sorted(
        level.price for level in snapshot.asks
    )
