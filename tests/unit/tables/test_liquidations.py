"""The liquidations table: events and the stream's heartbeat (REQ-WP-094, spec 146).

Both live in one table because they answer one question together: what was liquidated, and was
anyone listening. An event row without a heartbeat row in its neighbourhood is a number; a quiet
window is only a reading where heartbeats say the stream was up.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import EventMeta, LiquidationEvent
from channelflow.lakehouse import Catalog
from channelflow.tables import liquidations as table

MS = 1_000_000
MINUTE = 60_000_000_000


def event(
    *,
    at: int = 1_000 * MS,
    ingest: int = 1_001 * MS,
    venue: str = "binance",
    symbol: str = "BTCUSDT",
    side: str = "long_liquidated",
    price: str = "100.5",
    qty: str = "2",
) -> LiquidationEvent:
    return LiquidationEvent(
        meta=EventMeta(
            source=f"{venue}-ws-liquidation",
            venue=venue,
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=ingest,
            sequence=None,
            source_event_id=None,
        ),
        side=side,  # type: ignore[arg-type]
        price=Decimal(price),
        qty=Decimal(qty),
        notional_usd=Decimal(price) * Decimal(qty),
    )


@pytest.mark.trace("REQ-WP-094")
def test_the_schema_is_section_10_5_plus_the_kind_and_both_times() -> None:
    assert table.SCHEMA.names == (
        "event_time_ns",
        "ingest_time_ns",
        "venue",
        "symbol",
        "market_type",
        "source",
        "kind",
        "side",
        "price",
        "qty",
        "notional_usd",
    )
    assert table.SCHEMA.event_time_column == "event_time_ns"
    assert table.TABLE_NAME == "liquidations"


@pytest.mark.trace("REQ-WP-094")
def test_an_event_round_trips_exactly_with_decimals() -> None:
    original = event(price="83015.40", qty="0.012")
    row = table.event_row(original)

    assert row["kind"] == "event" and row["side"] == "long_liquidated"
    assert isinstance(row["price"], Decimal) and row["price"] == Decimal("83015.40")
    assert row["event_time_ns"] == 1_000 * MS and row["ingest_time_ns"] == 1_001 * MS
    assert table.from_row(row) == original


@pytest.mark.trace("REQ-WP-094")
def test_a_heartbeat_has_no_side_price_or_quantity_and_round_trips() -> None:
    beat = table.Heartbeat(venue="okx", symbol="BTC-USDT-SWAP", at_ns=5 * MINUTE)
    row = table.heartbeat_row(beat)

    assert row["kind"] == "heartbeat"
    assert row["side"] is None and row["price"] is None and row["qty"] is None
    assert row["notional_usd"] is None
    assert row["event_time_ns"] == 5 * MINUTE == row["ingest_time_ns"]
    assert table.from_row(row) == beat


@pytest.mark.trace("REQ-WP-094")
def test_the_sink_stores_an_event_once_even_if_the_venue_replays_it_after_a_reconnect(
    catalog: Catalog,
) -> None:
    sink = table.LiquidationSink(table.table_for(catalog))
    sink(event())
    sink(event())
    sink(event(ingest=9_999 * MS))  # the same event received again, later
    assert sink.pending == 1
    sink.flush()

    again = table.LiquidationSink(table.table_for(catalog))
    again(event())
    assert again.pending == 0
    assert table.table_for(catalog).read().num_rows == 1


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize(
    "different",
    [
        {"at": 1_001 * MS},
        {"venue": "bybit"},
        {"symbol": "ETHUSDT"},
        {"side": "short_liquidated"},
        {"price": "100.6"},
        {"qty": "3"},
    ],
)
def test_two_events_that_differ_in_any_identifying_field_are_two_events(
    catalog: Catalog, different: dict[str, object]
) -> None:
    sink = table.LiquidationSink(table.table_for(catalog))
    sink(event())
    sink(event(**different))  # type: ignore[arg-type]
    assert sink.pending == 2


@pytest.mark.trace("REQ-WP-094")
def test_a_heartbeat_is_stored_once_per_symbol_per_minute(catalog: Catalog) -> None:
    sink = table.LiquidationSink(table.table_for(catalog))
    beat = table.Heartbeat(venue="binance", symbol="BTCUSDT", at_ns=MINUTE)
    sink.heartbeat(beat)
    sink.heartbeat(beat)
    sink.heartbeat(table.Heartbeat(venue="binance", symbol="ETHUSDT", at_ns=MINUTE))
    sink.heartbeat(table.Heartbeat(venue="binance", symbol="BTCUSDT", at_ns=2 * MINUTE))
    assert sink.pending == 3


@pytest.mark.trace("REQ-WP-094")
def test_an_event_and_a_heartbeat_at_the_same_instant_do_not_collide(catalog: Catalog) -> None:
    sink = table.LiquidationSink(table.table_for(catalog))
    sink(event(at=MINUTE))
    sink.heartbeat(table.Heartbeat(venue="binance", symbol="BTCUSDT", at_ns=MINUTE))
    assert sink.pending == 2


@pytest.mark.trace("REQ-WP-094")
def test_events_and_heartbeats_are_read_back_by_market_and_sorted(catalog: Catalog) -> None:
    sink = table.LiquidationSink(table.table_for(catalog))
    sink(event(at=3 * MS))
    sink(event(at=1 * MS, price="1"))
    sink(event(at=2 * MS, symbol="ETHUSDT"))
    sink.heartbeat(table.Heartbeat(venue="binance", symbol="BTCUSDT", at_ns=2 * MINUTE))
    sink.heartbeat(table.Heartbeat(venue="binance", symbol="BTCUSDT", at_ns=1 * MINUTE))
    sink.flush()

    events, beats = table.read(table.table_for(catalog))

    assert set(events) == {("binance", "BTCUSDT"), ("binance", "ETHUSDT")}
    assert [e.meta.event_time_ns for e in events[("binance", "BTCUSDT")]] == [1 * MS, 3 * MS]
    assert beats == {("binance", "BTCUSDT"): [1 * MINUTE, 2 * MINUTE]}


@pytest.mark.trace("REQ-WP-094")
def test_an_empty_flush_commits_nothing_and_a_flush_clears_the_buffer(catalog: Catalog) -> None:
    sink = table.LiquidationSink(table.table_for(catalog))
    assert sink.flush() is None
    sink(event())
    assert sink.flush() is not None and sink.pending == 0 and sink.flush() is None


@pytest.mark.trace("REQ-WP-094")
def test_a_heartbeat_already_stored_is_recognised_by_a_new_sink(catalog: Catalog) -> None:
    first = table.LiquidationSink(table.table_for(catalog))
    beat = table.Heartbeat(venue="binance", symbol="BTCUSDT", at_ns=MINUTE)
    first.heartbeat(beat)
    first.flush()

    second = table.LiquidationSink(table.table_for(catalog))
    second.heartbeat(beat)

    assert second.pending == 0
