"""OKX v5 messages become the same canonical events (REQ-WP-044).

Every payload here is real traffic, recorded from the public venue.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from channelflow.connectors.okx import (
    NormalizationError,
    UnknownContractValue,
    contract_value,
    order_book_message,
    public_trade,
)
from channelflow.domain import BookDelta, BookSnapshot

VENUE = {"venue": "okx", "market_type": "swap"}
INGEST = 1_789_000_000_000_000_000
INSTRUMENT = "BTC-USDT-SWAP"


# --- size is in contracts ------------------------------------------------------


@pytest.mark.trace("REQ-WP-044")
def test_the_contract_value_comes_from_the_venue(instruments: dict[str, Any]) -> None:
    assert contract_value(instruments, inst_id=INSTRUMENT) == Decimal("0.01")


@pytest.mark.trace("REQ-WP-044")
def test_a_trade_size_is_converted_from_contracts_to_base_units(
    trade_messages: list[dict[str, Any]], instruments: dict[str, Any]
) -> None:
    """The reason this connector is not [[REQ-WP-043]] with a different URL.

    Binance and Bybit send a base-asset quantity; OKX sends contracts. Read the
    same way, every volume on this instrument would be a hundred times too
    large, and nothing downstream would show a symptom -- the numbers stay
    positive, ordered and plausible.
    """
    value = contract_value(instruments, inst_id=INSTRUMENT)
    raw = trade_messages[0]["data"][0]

    event = public_trade(raw, **VENUE, contract_value=value, ingest_time_ns=INGEST)

    assert event.qty_base == Decimal(raw["sz"]) * value
    assert event.qty_base != Decimal(raw["sz"])


@pytest.mark.trace("REQ-WP-044")
def test_the_notional_follows_the_converted_size(
    trade_messages: list[dict[str, Any]], instruments: dict[str, Any]
) -> None:
    """A notional computed from the raw contract count would be wrong by the
    same factor, and it is what every money figure downstream reads."""
    value = contract_value(instruments, inst_id=INSTRUMENT)
    raw = trade_messages[0]["data"][0]

    event = public_trade(raw, **VENUE, contract_value=value, ingest_time_ns=INGEST)

    assert event.notional_quote == event.price * event.qty_base


@pytest.mark.trace("REQ-WP-044")
def test_an_instrument_nobody_described_is_refused(instruments: dict[str, Any]) -> None:
    """Not defaulted to one. A default is right for some instruments and a
    hundredfold error on others, and the error has no symptom."""
    with pytest.raises(UnknownContractValue):
        contract_value(instruments, inst_id="ETH-USDT-SWAP")


@pytest.mark.trace("REQ-WP-044")
def test_a_contract_worth_nothing_is_refused(trade_messages: list[dict[str, Any]]) -> None:
    with pytest.raises(UnknownContractValue):
        public_trade(
            trade_messages[0]["data"][0],
            **VENUE,
            contract_value=Decimal(0),
            ingest_time_ns=INGEST,
        )


# --- what `side` means, measured -----------------------------------------------


@pytest.mark.trace("REQ-WP-044")
def test_a_buy_lifts_the_ask_and_a_sell_hits_the_bid(interleaved: list[dict[str, Any]]) -> None:
    """What `side` means, established from the recording rather than assumed.

    OKX's field table does not render through any fetchable documentation page.
    So the question is answered the way it can be answered: replay the
    interleaved stream, maintain the book, and see where each side's trades
    execute. A taker buying lifts the ask; a taker selling hits the bid.

    Asserted here rather than written in a docstring, because a test fails when
    the venue changes and prose does not.
    """
    bids: dict[Decimal, Decimal] = {}
    asks: dict[Decimal, Decimal] = {}
    seen = {"buy": [0, 0], "sell": [0, 0]}  # [at or above ask, at or below bid]

    def apply(rows: list[Any], book: dict[Decimal, Decimal]) -> None:
        for row in rows:
            price, size = Decimal(row[0]), Decimal(row[1])
            if size == 0:
                book.pop(price, None)
            else:
                book[price] = size

    for message in interleaved:
        channel = message["arg"]["channel"]
        if channel == "books":
            for data in message["data"]:
                if message.get("action") == "snapshot":
                    bids.clear()
                    asks.clear()
                apply(data.get("bids", []), bids)
                apply(data.get("asks", []), asks)
        elif channel == "trades" and bids and asks:
            best_bid, best_ask = max(bids), min(asks)
            for data in message["data"]:
                price, side = Decimal(data["px"]), data["side"]
                if price >= best_ask:
                    seen[side][0] += 1
                elif price <= best_bid:
                    seen[side][1] += 1

    buys_at_ask, buys_at_bid = seen["buy"]
    sells_at_ask, sells_at_bid = seen["sell"]

    assert buys_at_ask + sells_at_bid > 0, "the recording must contain trades on both sides"
    # Overwhelming rather than absolute: a trade can arrive before the delta
    # that had already moved the price, which is what an interleaved recording
    # looks like and not a counter-example.
    assert buys_at_ask > buys_at_bid * 5
    assert sells_at_bid > sells_at_ask * 5


@pytest.mark.trace("REQ-WP-044")
def test_the_aggressor_is_the_taker_and_the_maker_follows(
    trade_messages: list[dict[str, Any]], instruments: dict[str, Any]
) -> None:
    value = contract_value(instruments, inst_id=INSTRUMENT)

    for message in trade_messages:
        for raw in message["data"]:
            event = public_trade(raw, **VENUE, contract_value=value, ingest_time_ns=INGEST)

            assert event.aggressor_side == raw["side"]
            assert event.is_buyer_maker is (raw["side"] == "sell")


@pytest.mark.trace("REQ-WP-044")
def test_an_unknown_side_is_refused(
    trade_messages: list[dict[str, Any]], instruments: dict[str, Any]
) -> None:
    raw = dict(trade_messages[0]["data"][0])
    raw["side"] = "cross"

    with pytest.raises(NormalizationError, match="taker side"):
        public_trade(
            raw,
            **VENUE,
            contract_value=contract_value(instruments, inst_id=INSTRUMENT),
            ingest_time_ns=INGEST,
        )


# --- clocks and the book -------------------------------------------------------


@pytest.mark.trace("REQ-WP-044")
def test_the_event_time_is_the_venue_s_and_ingestion_is_ours(
    trade_messages: list[dict[str, Any]], instruments: dict[str, Any]
) -> None:
    raw = trade_messages[0]["data"][0]

    event = public_trade(
        raw,
        **VENUE,
        contract_value=contract_value(instruments, inst_id=INSTRUMENT),
        ingest_time_ns=INGEST,
    )

    assert event.meta.event_time_ns == int(raw["ts"]) * 1_000_000
    assert event.meta.ingest_time_ns == INGEST


@pytest.mark.trace("REQ-WP-044")
def test_the_first_book_message_is_a_snapshot_and_the_rest_are_updates(
    book_messages: list[dict[str, Any]],
) -> None:
    events = [order_book_message(m, **VENUE, ingest_time_ns=INGEST) for m in book_messages]

    assert isinstance(events[0], BookSnapshot)
    assert all(isinstance(e, BookDelta) for e in events[1:])


@pytest.mark.trace("REQ-WP-044")
def test_the_venue_states_what_came_before_each_update(book_messages: list[dict[str, Any]]) -> None:
    """OKX carries an explicit chain: every `prevSeqId` is the previous
    message's `seqId`. Stronger than either neighbour -- Binance sends a range
    and Bybit a single incrementing id -- so a gap is detectable without
    remembering anything."""
    ids = [m["data"][0]["seqId"] for m in book_messages]
    prevs = [m["data"][0]["prevSeqId"] for m in book_messages]

    assert prevs[0] == -1
    assert prevs[1:] == ids[:-1]


@pytest.mark.trace("REQ-WP-044")
def test_a_snapshot_has_no_predecessor(book_messages: list[dict[str, Any]]) -> None:
    first = order_book_message(book_messages[1], **VENUE, ingest_time_ns=INGEST)
    assert isinstance(first, BookDelta)

    assert first.prev_update_id == book_messages[0]["data"][0]["seqId"]


@pytest.mark.trace("REQ-WP-044")
def test_the_bids_are_the_bids(book_messages: list[dict[str, Any]]) -> None:
    """Swapped sides reconstruct cleanly, pass every sequencing test and invert
    the spread -- arithmetically fine and economically impossible."""
    snapshot = order_book_message(book_messages[0], **VENUE, ingest_time_ns=INGEST)
    assert isinstance(snapshot, BookSnapshot)

    assert max(level.price for level in snapshot.bids) < min(level.price for level in snapshot.asks)


@pytest.mark.trace("REQ-WP-044")
def test_an_unknown_action_is_refused(book_messages: list[dict[str, Any]]) -> None:
    message = dict(book_messages[0])
    message["action"] = "rewrite"

    with pytest.raises(NormalizationError, match="unknown action"):
        order_book_message(message, **VENUE, ingest_time_ns=INGEST)
