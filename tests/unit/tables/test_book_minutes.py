"""The book-minutes table and the quotes a minute implies (REQ-WP-095, spec 147)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.context.minute_book import MinuteSummary
from channelflow.lakehouse import Catalog
from channelflow.tables import book_minutes as table
from channelflow.tables import quotes as quotes_table

MINUTE = 60_000_000_000
T0 = 1_791_700_000_000_000_000


def summary(
    *,
    close: int = T0 + MINUTE,
    venue: str = "bybit",
    symbol: str = "BTCUSDT",
    frames: int = 120,
    observations: int = 58,
    ofi: str | None = "3.5",
    di: float | None = 0.08,
    bid: str | None = "100",
    ask: str | None = "101",
    mid: str | None = "100.5",
    quote_time: int | None = T0 + MINUTE - 1_000_000,
) -> MinuteSummary:
    return MinuteSummary(
        venue=venue,
        symbol=symbol,
        minute_close_ns=close,
        frames=frames,
        observations=observations,
        ofi=None if ofi is None else Decimal(ofi),
        depth_imbalance_10=di,
        bid=None if bid is None else Decimal(bid),
        ask=None if ask is None else Decimal(ask),
        mid=None if mid is None else Decimal(mid),
        quote_time_ns=quote_time,
    )


def sink_for(catalog: Catalog) -> table.BookMinuteSink:
    return table.BookMinuteSink(table.table_for(catalog), quotes_table.table_for(catalog))


@pytest.mark.trace("REQ-WP-095")
def test_the_schema_has_the_minute_its_two_times_and_what_it_amounted_to() -> None:
    assert table.SCHEMA.names == (
        "minute_close_ns",
        "ingest_time_ns",
        "venue",
        "symbol",
        "market_type",
        "source",
        "frames",
        "observations",
        "ofi",
        "depth_imbalance_10",
        "bid",
        "ask",
        "mid",
        "quote_time_ns",
    )
    assert table.SCHEMA.event_time_column == "minute_close_ns"
    assert table.TABLE_NAME == "book_minutes"


@pytest.mark.trace("REQ-WP-095")
def test_a_row_carries_the_minute_the_receipt_and_decimals_exactly() -> None:
    row = table.to_row(summary(ofi="3.50"), ingest_time_ns=T0 + MINUTE + 500, market_type="perp")

    assert row["minute_close_ns"] == T0 + MINUTE and row["ingest_time_ns"] == T0 + MINUTE + 500
    assert row["source"] == "bybit-ws-book" and row["market_type"] == "perp"
    assert row["ofi"] == Decimal("3.50") and isinstance(row["mid"], Decimal)


@pytest.mark.trace("REQ-WP-095")
def test_a_row_round_trips_and_an_absent_value_stays_absent() -> None:
    row = table.to_row(
        summary(ofi=None, di=None, mid=None, bid=None, ask=None),
        ingest_time_ns=1,
        market_type="perp",
    )
    minute = table.from_row(row)

    assert minute.ofi is None and minute.depth_imbalance_10 is None and minute.mid is None
    assert minute.frames == 120 and minute.observations == 58


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_with_a_quote_also_writes_the_quote_with_the_two_times_apart() -> None:
    quote = table.quote_of(summary(), ingest_time_ns=T0 + MINUTE + 9)

    assert quote is not None
    assert (quote.bid, quote.ask, quote.mid) == (Decimal(100), Decimal(101), Decimal("100.5"))
    assert quote.ts_ns == T0 + MINUTE - 1_000_000  # the venue's time of the last message
    assert quote.ingest_ns == T0 + MINUTE + 9  # ours, and never the same thing


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_without_a_top_of_book_writes_no_quote() -> None:
    assert table.quote_of(summary(bid=None, ask=None, mid=None), ingest_time_ns=1) is None


@pytest.mark.trace("REQ-WP-095")
def test_the_sink_stores_a_minute_and_its_quote_once(catalog: Catalog) -> None:
    sink = sink_for(catalog)
    sink(summary(), ingest_time_ns=T0 + MINUTE + 1, market_type="perp")
    sink(summary(), ingest_time_ns=T0 + MINUTE + 2, market_type="perp")
    assert sink.pending == 2  # the minute and its quote, not twice
    assert sink.flush() is not None and sink.pending == 0

    again = sink_for(catalog)
    again(summary(), ingest_time_ns=T0 + MINUTE + 3, market_type="perp")
    assert again.pending == 0
    assert table.table_for(catalog).read().num_rows == 1
    assert quotes_table.table_for(catalog).read().num_rows == 1


@pytest.mark.trace("REQ-WP-095")
@pytest.mark.parametrize(
    "different", [{"close": T0 + 2 * MINUTE}, {"venue": "okx"}, {"symbol": "ETHUSDT"}]
)
def test_minutes_that_differ_in_venue_symbol_or_time_are_different_minutes(
    catalog: Catalog, different: dict[str, object]
) -> None:
    sink = sink_for(catalog)
    sink(summary(), ingest_time_ns=1, market_type="perp")
    sink(summary(**different), ingest_time_ns=1, market_type="perp")  # type: ignore[arg-type]
    assert sink.pending == 4


@pytest.mark.trace("REQ-WP-095")
def test_an_empty_minute_is_stored_as_a_count_of_zero_and_writes_no_quote(catalog: Catalog) -> None:
    sink = sink_for(catalog)
    empty = summary(
        frames=0, observations=0, ofi=None, di=None, bid=None, ask=None, mid=None, quote_time=None
    )
    sink(empty, ingest_time_ns=1, market_type="perp")
    sink.flush()

    assert table.table_for(catalog).read().num_rows == 1
    assert quotes_table.table_for(catalog).read().num_rows == 0


@pytest.mark.trace("REQ-WP-095")
def test_minutes_are_read_back_by_market_oldest_first(catalog: Catalog) -> None:
    sink = sink_for(catalog)
    for close in (T0 + 3 * MINUTE, T0 + 1 * MINUTE, T0 + 2 * MINUTE):
        sink(summary(close=close), ingest_time_ns=1, market_type="perp")
    sink(summary(venue="okx"), ingest_time_ns=1, market_type="perp")
    sink.flush()

    minutes = table.read_minutes(table.table_for(catalog))

    assert set(minutes) == {("bybit", "BTCUSDT"), ("okx", "BTCUSDT")}
    assert [m.minute_close_ns for m in minutes[("bybit", "BTCUSDT")]] == [
        T0 + 1 * MINUTE,
        T0 + 2 * MINUTE,
        T0 + 3 * MINUTE,
    ]


@pytest.mark.trace("REQ-WP-095")
def test_a_flush_with_nothing_pending_commits_nothing(catalog: Catalog) -> None:
    assert sink_for(catalog).flush() is None
