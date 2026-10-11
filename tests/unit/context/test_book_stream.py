"""A venue's order-book stream as a collector task (REQ-WP-095, spec 147).

The frames are the three venues' real ones, recorded 2026-10-11. What is pinned: which stream each
venue is connected to and why; that each frame becomes the project's own `BookSnapshot` or
`BookDelta`; that OKX's contracts become base units; and that a lost sequence makes the connection
be remade rather than a wrong book being trusted.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from channelflow.connectors.session import FakeClock
from channelflow.context import book as book_stream
from channelflow.domain import BookDelta, BookSnapshot
from channelflow.lakehouse import Catalog
from channelflow.tables import book_minutes as table
from channelflow.tables import quotes as quotes_table
from tests.unit.context.doubles import load
from tests.unit.context.test_streams import FakeConnector

SECOND = 1_000_000_000
MINUTE = 60 * SECOND
CT_VAL = {"BTC-USDT-SWAP": Decimal("0.01")}


# --- what each venue is connected to -----------------------------------------------------------


@pytest.mark.trace("REQ-WP-095")
def test_binance_is_the_spot_partial_depth_stream_of_each_symbol_on_the_combined_endpoint() -> None:
    spec = book_stream.stream_spec("binance", ["BTCUSDT", "ETHUSDT"])

    assert spec.url == (
        "wss://stream.binance.com:9443/stream?streams=btcusdt@depth10@1000ms/ethusdt@depth10@1000ms"
    )
    assert spec.subscribe_message is None


@pytest.mark.trace("REQ-WP-095")
def test_bybit_is_the_linear_fifty_level_book_one_topic_per_symbol() -> None:
    spec = book_stream.stream_spec("bybit", ["BTCUSDT"])

    assert spec.url == "wss://stream.bybit.com/v5/public/linear"
    assert json.loads(spec.subscribe_message or "") == {
        "op": "subscribe",
        "args": ["orderbook.50.BTCUSDT"],
    }


@pytest.mark.trace("REQ-WP-095")
def test_okx_is_the_books_channel_which_has_ten_levels_not_books5_which_has_five() -> None:
    spec = book_stream.stream_spec("okx", ["BTC-USDT-SWAP"])

    assert json.loads(spec.subscribe_message or "")["args"] == [
        {"channel": "books", "instId": "BTC-USDT-SWAP"}
    ]


@pytest.mark.trace("REQ-WP-095")
def test_each_venues_book_is_of_the_market_its_series_is() -> None:
    assert book_stream.MARKET_TYPE == {"binance": "spot", "bybit": "perp", "okx": "perp"}


@pytest.mark.trace("REQ-WP-095")
def test_an_unknown_venue_has_no_book_stream() -> None:
    with pytest.raises(ValueError, match="kraken"):
        book_stream.stream_spec("kraken", [])
    with pytest.raises(ValueError, match="kraken"):
        book_stream.message_of("kraken", {}, 1, {})


# --- frames to the project's own messages --------------------------------------------------------


@pytest.mark.trace("REQ-WP-095")
def test_a_recorded_binance_frame_is_a_ten_level_snapshot_of_the_symbol_in_its_stream_name() -> (
    None
):
    for frame in load("ws4_binance_spot_depth10_combined"):
        symbol, message = book_stream.message_of("binance", frame, 77, {})  # type: ignore[misc]

        assert isinstance(message, BookSnapshot)
        assert symbol == frame["stream"].split("@")[0].upper()
        assert (len(message.bids), len(message.asks)) == (10, 10)
        assert message.meta.market_type == "spot" and message.meta.source == "binance-ws-depth"
        assert message.meta.ingest_time_ns == message.meta.event_time_ns == 77  # no venue timestamp


@pytest.mark.trace("REQ-WP-095")
def test_recorded_bybit_frames_are_a_snapshot_then_deltas_with_a_continuous_sequence() -> None:
    frames = [f for f in load("ws4_bybit_orderbook50") if "topic" in f]
    messages = [book_stream.message_of("bybit", f, 1, {})[1] for f in frames]  # type: ignore[index]

    assert isinstance(messages[0], BookSnapshot) and len(messages[0].bids) == 50
    assert all(isinstance(m, BookDelta) for m in messages[1:])
    ids = [messages[0].update_id] + [m.final_update_id for m in messages[1:]]  # type: ignore[union-attr]
    assert all(b == a + 1 for a, b in zip(ids, ids[1:], strict=False))
    assert messages[0].meta.market_type == "perp"


@pytest.mark.trace("REQ-WP-095")
def test_bybit_acknowledgements_are_not_book_messages() -> None:
    ack = [f for f in load("ws4_bybit_orderbook50") if "topic" not in f][0]
    assert book_stream.message_of("bybit", ack, 1, {}) is None


@pytest.mark.trace("REQ-WP-095")
def test_recorded_okx_frames_become_a_snapshot_then_updates_with_sizes_in_base_units() -> None:
    frames = [f for f in load("ws4_okx_books") if "action" in f]
    raw_first_ask = Decimal(frames[0]["data"][0]["asks"][0][1])

    symbol, snapshot = book_stream.message_of("okx", frames[0], 1, CT_VAL)  # type: ignore[misc]

    assert symbol == "BTC-USDT-SWAP" and isinstance(snapshot, BookSnapshot)
    assert snapshot.asks[0].qty == raw_first_ask * Decimal("0.01")  # contracts -> BTC
    rest = [book_stream.message_of("okx", f, 1, CT_VAL)[1] for f in frames[1:]]  # type: ignore[index]
    assert all(isinstance(m, BookDelta) for m in rest)


@pytest.mark.trace("REQ-WP-095")
def test_okx_without_a_contract_value_refuses_rather_than_reading_contracts_as_base_units() -> None:
    frame = [f for f in load("ws4_okx_books") if "action" in f][0]
    with pytest.raises(ValueError, match="BTC-USDT-SWAP"):
        book_stream.message_of("okx", frame, 1, {})
    with pytest.raises(ValueError, match="BTC-USDT-SWAP"):
        book_stream.message_of("okx", frame, 1, {"BTC-USDT-SWAP": None})


@pytest.mark.trace("REQ-WP-095")
def test_okx_acks_and_other_channels_are_not_book_messages() -> None:
    ack = [f for f in load("ws4_okx_books") if "event" in f][0]
    assert book_stream.message_of("okx", ack, 1, CT_VAL) is None
    other = {"arg": {"channel": "trades", "instId": "BTC-USDT-SWAP"}, "data": [{}]}
    assert book_stream.message_of("okx", other, 1, CT_VAL) is None


# --- the task ----------------------------------------------------------------------------------


def task_for(
    catalog: Catalog,
    venue: str,
    symbols: list[str],
    *,
    start_ns: int = 1_791_700_000 * SECOND,
    contract_values: dict[str, Decimal | None] | None = None,
) -> tuple[Any, FakeConnector, FakeClock, table.BookMinuteSink, list[str]]:
    clock = FakeClock(start_ns)
    connector = FakeConnector()
    sink = table.BookMinuteSink(table.table_for(catalog), quotes_table.table_for(catalog))
    failures: list[str] = []
    task = book_stream.book_task(
        venue=venue,
        symbols=symbols,
        sink=sink,
        now_ns=clock.now_ns,
        on_failure=failures.append,
        contract_values=contract_values,
        clock=clock,
        connector=connector,
    )
    task.start()
    return task, connector, clock, sink, failures


def binance_frame(symbol: str, at_second: int) -> str:
    """A spot depth frame for `symbol`; sizes move a little each second so the OFI has something."""
    bids = [[str(100 - i), str(5 + at_second % 3)] for i in range(10)]
    asks = [[str(101 + i), "3"] for i in range(10)]
    return json.dumps(
        {
            "stream": f"{symbol.lower()}@depth10@1000ms",
            "data": {"lastUpdateId": at_second, "bids": bids, "asks": asks},
        }
    )


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_of_frames_becomes_one_stored_minute_and_a_quote(catalog: Catalog) -> None:
    task, connector, clock, sink, failures = task_for(catalog, "binance", ["BTCUSDT"])
    for second in range(1, 66):
        clock.advance_ns(SECOND)
        connector.push(binance_frame("BTCUSDT", second))
        task.step()

    assert failures == []
    sink.flush()
    minutes = table.read_minutes(table.table_for(catalog))[("binance", "BTCUSDT")]
    assert len(minutes) == 1 and minutes[0].frames > 0 and minutes[0].observations > 0
    assert minutes[0].depth_imbalance_10 is not None
    assert quotes_table.table_for(catalog).read().num_rows == 1


@pytest.mark.trace("REQ-WP-095")
def test_a_frame_for_a_symbol_not_watched_is_ignored_even_across_a_minute_boundary(
    catalog: Catalog,
) -> None:
    task, connector, clock, sink, failures = task_for(catalog, "binance", ["BTCUSDT"])
    for second in range(1, 70):
        clock.advance_ns(SECOND)
        connector.push(binance_frame("ETHUSDT", second))
        task.step()

    assert sink.pending == 0 and failures == []


@pytest.mark.trace("REQ-WP-095")
def test_bybit_asks_for_every_symbol_watched() -> None:
    spec = book_stream.stream_spec("bybit", ["BTCUSDT", "ETHUSDT"])
    assert json.loads(spec.subscribe_message or "")["args"] == [
        "orderbook.50.BTCUSDT",
        "orderbook.50.ETHUSDT",
    ]


@pytest.mark.trace("REQ-WP-095")
def test_a_frame_that_is_not_json_is_counted_and_the_stream_goes_on(catalog: Catalog) -> None:
    task, connector, clock, _, failures = task_for(catalog, "binance", ["BTCUSDT"])
    connector.push("<html>")
    connector.push(binance_frame("BTCUSDT", 1))
    clock.advance_ns(SECOND)

    task.step()

    assert len(failures) == 1 and "JSONDecodeError" in failures[0]


@pytest.mark.trace("REQ-WP-095")
def test_a_silent_minute_is_stored_with_a_zero_count_by_the_clock(catalog: Catalog) -> None:
    task, connector, clock, sink, _ = task_for(catalog, "binance", ["BTCUSDT"])
    clock.advance_ns(SECOND)
    connector.push(binance_frame("BTCUSDT", 1))
    task.step()
    # nothing more arrives; the tick must close the minute the frame was in
    clock.advance_ns(MINUTE + 10 * SECOND)
    task.step()

    sink.flush()
    (minute,) = table.read_minutes(table.table_for(catalog))[("binance", "BTCUSDT")]
    assert minute.frames == 1


@pytest.mark.trace("REQ-WP-095")
def test_a_bybit_sequence_gap_closes_the_connection_so_a_fresh_snapshot_is_fetched(
    catalog: Catalog,
) -> None:
    frames = [f for f in load("ws4_bybit_orderbook50") if "topic" in f]
    task, connector, clock, _, _ = task_for(catalog, "bybit", ["BTCUSDT"])
    connector.push(json.dumps(frames[0]))
    connector.push(json.dumps(frames[1]))
    clock.advance_ns(SECOND)
    task.step()
    assert not connector.closed

    gapped = json.loads(json.dumps(frames[3]))  # skips frames[2]
    connector.push(json.dumps(gapped))
    clock.advance_ns(SECOND)
    task.step()

    assert connector.closed


@pytest.mark.trace("REQ-WP-095")
def test_a_reconnect_resets_every_book_so_no_flow_spans_the_gap(catalog: Catalog) -> None:
    task, connector, clock, _, _ = task_for(catalog, "binance", ["BTCUSDT"])
    handler = task.handler
    clock.advance_ns(SECOND)
    connector.push(binance_frame("BTCUSDT", 1))
    task.step()
    book = handler.books["BTCUSDT"]
    assert book.tick(now_ns=clock.now_ns()) == []

    connector.alive_flag = False
    clock.advance_ns(5 * SECOND)
    task.step()  # the session reconnects; the task tells the handler

    assert connector.connects == 2
    assert (
        book._service.book is None
    )  # a fresh book: nothing of the old one carries over  # noqa: SLF001


@pytest.mark.trace("REQ-WP-095")
def test_the_recorded_okx_frames_are_one_continuous_chain_and_never_ask_for_a_resync() -> None:
    """The first live OKX run reconnected every two seconds: its seqIds jump, and the book read
    the jump as a gap. The frames were always fine; this feeds them to the book."""
    from channelflow.context.minute_book import MinuteBook

    book = MinuteBook(venue="okx", symbol="BTC-USDT-SWAP")
    for frame in load("ws4_okx_books"):
        item = book_stream.message_of("okx", frame, 1, CT_VAL)
        if item is None:
            continue
        book.feed(item[1])
        assert not book.needs_resync


@pytest.mark.trace("REQ-WP-095")
def test_okxs_bare_pong_is_not_a_failed_frame(catalog: Catalog) -> None:
    task, connector, clock, _, failures = task_for(
        catalog, "okx", ["BTC-USDT-SWAP"], contract_values=CT_VAL
    )
    connector.push("pong")
    clock.advance_ns(SECOND)

    task.step()

    assert failures == []


# --- spot and swap, on one venue (REQ-WP-098) ---


@pytest.mark.trace("REQ-WP-098")
def test_the_market_type_of_a_book_is_asked_by_instrument_not_by_venue() -> None:
    assert book_stream.market_type_for("okx", "BTC-USDT") == "spot"
    assert book_stream.market_type_for("okx", "BTC-USDT-SWAP") == "perp"
    assert book_stream.market_type_for("binance", "BTCUSDT") == "spot"
    assert book_stream.market_type_for("bybit", "BTCUSDT") == "perp"


@pytest.mark.trace("REQ-WP-098")
def test_a_recorded_okx_spot_frame_keeps_its_sizes_because_they_are_already_base_units() -> None:
    frames = [f for f in load("ws5_okx_books_spot") if f.get("action") == "snapshot"]
    assert frames
    for frame in frames:
        raw = Decimal(frame["data"][0]["asks"][0][1])

        symbol, snapshot = book_stream.message_of("okx", frame, 1, {})  # type: ignore[misc]

        assert snapshot.asks[0].qty == raw  # unscaled
        assert snapshot.meta.market_type == "spot" and symbol == frame["arg"]["instId"]


@pytest.mark.trace("REQ-WP-098")
def test_a_spot_instrument_is_not_scaled_even_if_a_contract_value_is_offered_for_it() -> None:
    frame = [f for f in load("ws5_okx_books_spot") if f.get("action") == "snapshot"][0]
    raw = Decimal(frame["data"][0]["asks"][0][1])

    _, snapshot = book_stream.message_of("okx", frame, 1, {frame["arg"]["instId"]: Decimal("0.01")})  # type: ignore[misc]

    assert snapshot.asks[0].qty == raw


@pytest.mark.trace("REQ-WP-098")
def test_the_same_frame_shape_for_a_swap_is_scaled_and_labelled_perp() -> None:
    frame = [f for f in load("ws4_okx_books") if "action" in f][0]
    raw = Decimal(frame["data"][0]["asks"][0][1])

    _, snapshot = book_stream.message_of("okx", frame, 1, CT_VAL)  # type: ignore[misc]

    assert snapshot.asks[0].qty == raw * Decimal("0.01") and snapshot.meta.market_type == "perp"


@pytest.mark.trace("REQ-WP-098")
def test_okx_asks_for_every_book_symbol_in_one_subscription() -> None:
    spec = book_stream.stream_spec("okx", ["BTC-USDT", "ETH-USDT", "BTC-USDT-SWAP"])
    assert json.loads(spec.subscribe_message or "")["args"] == [
        {"channel": "books", "instId": "BTC-USDT"},
        {"channel": "books", "instId": "ETH-USDT"},
        {"channel": "books", "instId": "BTC-USDT-SWAP"},
    ]


@pytest.mark.trace("REQ-WP-098")
def test_each_minute_is_stored_with_its_own_instruments_market_type(catalog: Catalog) -> None:
    spot = [f for f in load("ws5_okx_books_spot") if f.get("arg", {}).get("instId") == "BTC-USDT"]
    swap = [f for f in load("ws4_okx_books") if "action" in f]
    # The frames carry the venue's own times, and a minute closes in event time: the clock starts at
    # the latest of them so that advancing it past a boundary closes the minute they are in.
    latest_ms = max(int(f["data"][0]["ts"]) for f in spot + swap if "data" in f)
    task, connector, clock, sink, _ = task_for(
        catalog,
        "okx",
        ["BTC-USDT", "BTC-USDT-SWAP"],
        contract_values=CT_VAL,
        start_ns=latest_ms * 1_000_000,
    )
    for frame in [f for f in spot if "action" in f] + swap:
        connector.push(json.dumps(frame))
    for _ in range(70):
        clock.advance_ns(SECOND)
        task.step()

    sink.flush()
    types = {
        row["symbol"]: row["market_type"] for row in table.table_for(catalog).read().to_pylist()
    }
    assert types == {"BTC-USDT": "spot", "BTC-USDT-SWAP": "perp"}
