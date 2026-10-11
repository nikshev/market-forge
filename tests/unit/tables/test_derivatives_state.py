"""The derivatives-state table (REQ-WP-093): PRD §10.4 as rows, its two times kept apart."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import DerivativesState, EventMeta
from channelflow.lakehouse import Catalog
from channelflow.tables import derivatives_state as table

MS = 1_000_000


def state(
    *,
    at: int = 1_000 * MS,
    ingest: int = 2_000 * MS,
    source: str = "bybit-rest",
    venue: str = "bybit",
    symbol: str = "BTCUSDT",
    **fields: object,
) -> DerivativesState:
    return DerivativesState(
        meta=EventMeta(
            source=source,
            venue=venue,
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=ingest,
            sequence=None,
            source_event_id=None,
        ),
        **fields,  # type: ignore[arg-type]
    )


@pytest.mark.trace("REQ-WP-093")
def test_the_schema_is_section_10_4_plus_the_source_and_both_times() -> None:
    assert table.SCHEMA.names == (
        "event_time_ns",
        "ingest_time_ns",
        "venue",
        "symbol",
        "market_type",
        "source",
        "mark_price",
        "index_price",
        "funding_rate",
        "next_funding_time_ns",
        "open_interest_base",
        "open_interest_usd",
        "basis_bps",
    )
    assert table.SCHEMA.event_time_column == "event_time_ns"
    assert table.TABLE_NAME == "derivatives_state"


@pytest.mark.trace("REQ-WP-093")
def test_prices_are_decimal_and_a_row_round_trips_exactly() -> None:
    original = state(
        mark_price=Decimal("83015.40"),
        index_price=Decimal("83050.79"),
        funding_rate=-0.00002718,
        next_funding_time_ns=5 * MS,
        open_interest_base=56214.576,
        open_interest_usd=4666675512.47,
        basis_bps=-4.26,
    )
    row = table.to_row(original)

    assert row["mark_price"] == Decimal("83015.40")
    assert isinstance(row["mark_price"], Decimal)
    assert row["event_time_ns"] == 1_000 * MS and row["ingest_time_ns"] == 2_000 * MS
    assert table.from_row(row) == original


@pytest.mark.trace("REQ-WP-093")
def test_an_absent_field_stays_absent_and_is_never_a_default() -> None:
    row = table.to_row(state(open_interest_usd=1.0))
    assert row["funding_rate"] is None and row["mark_price"] is None
    restored = table.from_row(row)
    assert restored.funding_rate is None and restored.mark_price is None
    assert restored.open_interest_usd == 1.0


@pytest.mark.trace("REQ-WP-093")
def test_the_sink_stores_a_state_once_however_often_it_is_offered(catalog: Catalog) -> None:
    sink = table.DerivativesStateSink(table.table_for(catalog))
    first = state(funding_rate=0.1)

    sink(first)
    sink(first)
    sink(state(funding_rate=0.2))  # same venue, symbol, time and source: the same state
    assert sink.pending == 1
    assert sink.flush() is not None
    assert sink.flush() is None  # nothing buffered: no empty commit

    sink(first)  # offered again after the flush
    assert sink.pending == 0
    assert table.table_for(catalog).read().num_rows == 1


@pytest.mark.trace("REQ-WP-093")
def test_identity_is_venue_symbol_time_and_source(catalog: Catalog) -> None:
    sink = table.DerivativesStateSink(table.table_for(catalog))
    sink(state())
    sink(state(source="bybit-funding-history"))
    sink(state(at=1_001 * MS))
    sink(state(symbol="ETHUSDT"))
    sink(state(venue="okx"))
    assert sink.pending == 5


@pytest.mark.trace("REQ-WP-093")
def test_a_new_sink_knows_what_an_earlier_one_stored(catalog: Catalog) -> None:
    first = table.DerivativesStateSink(table.table_for(catalog))
    first(state())
    first.flush()

    second = table.DerivativesStateSink(table.table_for(catalog))
    second(state())
    assert second.pending == 0


@pytest.mark.trace("REQ-WP-093")
def test_states_are_read_back_grouped_by_market_and_sorted_by_event_time(catalog: Catalog) -> None:
    sink = table.DerivativesStateSink(table.table_for(catalog))
    sink(state(at=3 * MS, funding_rate=3.0))
    sink(state(at=1 * MS, funding_rate=1.0))
    sink(state(at=2 * MS, symbol="ETHUSDT", funding_rate=9.0))
    sink.flush()

    grouped = table.read_states(table.table_for(catalog))

    assert set(grouped) == {("bybit", "BTCUSDT"), ("bybit", "ETHUSDT")}
    assert [s.meta.event_time_ns for s in grouped[("bybit", "BTCUSDT")]] == [1 * MS, 3 * MS]
