"""The top-of-book quotes table: one row per quote, its two times kept apart (REQ-WP-091)."""

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa
import pytest

from channelflow.tables import quotes

TS_NS = 1_788_838_800_000_000_000
INGEST_NS = TS_NS + 123_456


def quote() -> quotes.Quote:
    return quotes.Quote(
        venue="binance",
        symbol="ETHUSDT",
        bid=Decimal("2400.10"),
        ask=Decimal("2400.20"),
        mid=Decimal("2400.15"),
        ts_ns=TS_NS,
        ingest_ns=INGEST_NS,
    )


@pytest.mark.trace("REQ-WP-091")
def test_the_table_is_named_quotes() -> None:
    assert quotes.TABLE_NAME == "quotes"


@pytest.mark.trace("REQ-WP-091")
def test_the_schema_is_exactly_the_seven_columns_with_exchange_time_as_event_time() -> None:
    assert [(c.name, c.type) for c in quotes.SCHEMA.columns] == [
        ("venue", "string"),
        ("symbol", "string"),
        ("bid", "decimal"),
        ("ask", "decimal"),
        ("mid", "decimal"),
        # `timestamp_ns` is the storage vocabulary's name for an event time;
        # physically it is the int64 nanosecond count below. The schema refuses
        # any other type on the event-time column, because a point-in-time
        # filter compares nanosecond counts.
        ("ts_ns", "timestamp_ns"),
        ("ingest_ns", "int64"),
    ]
    assert quotes.SCHEMA.event_time_column == "ts_ns"
    assert quotes.SCHEMA.arrow().field("ts_ns").type == pa.int64()


@pytest.mark.trace("REQ-WP-091")
def test_to_row_maps_the_quote_with_exchange_time_and_receive_time_apart() -> None:
    row = quotes.to_row(quote())

    assert row == {
        "venue": "binance",
        "symbol": "ETHUSDT",
        "bid": Decimal("2400.10"),
        "ask": Decimal("2400.20"),
        "mid": Decimal("2400.15"),
        "ts_ns": TS_NS,
        "ingest_ns": INGEST_NS,
    }
    # Principle II: the two times are distinct and each keeps its own name --
    # a row where they were swapped would still "have" two timestamps.
    assert row["ts_ns"] != row["ingest_ns"]


@pytest.mark.trace("REQ-WP-091")
def test_prices_are_decimal_and_never_float() -> None:
    row = quotes.to_row(quote())

    for name in ("bid", "ask", "mid"):
        assert isinstance(row[name], Decimal), name
        assert not isinstance(row[name], float), name
