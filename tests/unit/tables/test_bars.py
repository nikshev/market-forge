"""PRD §29.4's `bars` as a canonical table (REQ-TBL-001)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar, BarBuilder
from channelflow.lakehouse import InMemoryObjectStore, Table
from channelflow.tables import (
    ORDER,
    SCHEMA,
    BarSink,
    UnfinalizedBar,
    from_row,
    read_bars,
    table_for,
    to_row,
    write_bars,
)

MINUTE_NS = 60 * 1_000_000_000


def bar(
    index: int, *, price: str = "112000.10", final: bool = True, symbol: str = "BTCUSDT"
) -> Bar:
    open_ns = index * MINUTE_NS
    return Bar(
        venue="binance",
        symbol=symbol,
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=open_ns + MINUTE_NS,
        open=Decimal(price),
        high=Decimal(price) + Decimal("5"),
        low=Decimal(price) - Decimal("5"),
        close=Decimal(price) + Decimal("1"),
        volume_base=Decimal("1.5"),
        volume_quote=Decimal("168000.15"),
        trade_count=42,
        aggressive_buy_base=Decimal("0.9"),
        aggressive_sell_base=Decimal("0.6"),
        delta_base=Decimal("0.3"),
        vwap=Decimal("112000.55"),
        high_time_ns=open_ns + 10,
        low_time_ns=open_ns + 20,
        first_trade_id="t1",
        last_trade_id="t9",
        is_final=final,
    )


@pytest.fixture
def table() -> Table:
    return table_for(InMemoryObjectStore())


@pytest.mark.trace("REQ-TBL-001")
def test_a_bar_survives_the_round_trip_exactly(table: Table) -> None:
    """Every field, and the decimals as decimals.

    A canonical table that rounded a price on the way in would make every
    downstream figure wrong by an amount nobody could reconstruct.
    """
    original = bar(1)
    write_bars(table, [original])

    assert read_bars(table) == [original]


@pytest.mark.trace("REQ-TBL-001")
def test_a_price_that_float64_cannot_hold_comes_back_unchanged(table: Table) -> None:
    """`0.1` is the standard example and it is not academic here: a bar is money,
    and a table storing it as a float would return a different number."""
    exact = bar(1, price="0.1")
    write_bars(table, [exact])

    restored = read_bars(table)[0]
    assert restored.open == Decimal("0.1")
    assert str(restored.open) == "0.1"


@pytest.mark.trace("REQ-TBL-001")
def test_an_unfinalized_bar_is_refused(table: Table) -> None:
    """A canonical table holding a bar that may still change holds a row that
    will be rewritten, which is the repainting PRD §0.5 forbids."""
    with pytest.raises(UnfinalizedBar, match="not final"):
        to_row(bar(1, final=False))


@pytest.mark.trace("REQ-TBL-001")
def test_every_stored_bar_reads_back_final(table: Table) -> None:
    """`is_final` is not a column: every row here is final, so a column holding
    `true` on every row would be a field nobody reads and a door left open."""
    write_bars(table, [bar(1)])

    assert "is_final" not in SCHEMA.names
    assert read_bars(table)[0].is_final


@pytest.mark.trace("REQ-TBL-001")
def test_rows_come_back_in_the_order_the_prd_names(table: Table) -> None:
    """PRD §29.4: `(venue, symbol, timeframe, open_time)`. Two readers of one
    snapshot see the same series in the same order."""
    assert ORDER == ("venue", "symbol", "timeframe_ns", "open_time_ns")
    write_bars(table, [bar(3, symbol="ETHUSDT"), bar(2), bar(1)])

    read = read_bars(table)

    assert [(b.symbol, b.open_time_ns) for b in read] == [
        ("BTCUSDT", 1 * MINUTE_NS),
        ("BTCUSDT", 2 * MINUTE_NS),
        ("ETHUSDT", 3 * MINUTE_NS),
    ]


@pytest.mark.trace("REQ-TBL-001")
def test_a_point_in_time_read_uses_the_close_and_not_the_open(table: Table) -> None:
    """A bar becomes knowable when it closes.

    Filtering on `open_time_ns` would return a window that had opened and not
    finished at the instant asked for -- a bar whose high, low and close had not
    happened yet, handed over as if they had.
    """
    write_bars(table, [bar(1)])
    closes_at = 2 * MINUTE_NS

    assert read_bars(table, as_of_ns=closes_at) == [bar(1)]
    assert read_bars(table, as_of_ns=closes_at - 1) == []


@pytest.mark.trace("REQ-TBL-001")
def test_a_read_can_be_narrowed_to_one_series(table: Table) -> None:
    write_bars(table, [bar(1), bar(2, symbol="ETHUSDT")])

    assert [b.symbol for b in read_bars(table, symbol="BTCUSDT")] == ["BTCUSDT"]
    assert read_bars(table, venue="bybit") == []
    assert read_bars(table, timeframe_ns=MINUTE_NS * 5) == []


@pytest.mark.trace("REQ-TBL-001")
def test_the_sink_buffers_and_commits_once(table: Table) -> None:
    """A commit per bar would make the snapshot chain as long as the series, and
    a table with a manifest per row has metadata larger than its data."""
    sink = BarSink(table=table)
    for index in range(1, 4):
        sink(bar(index))

    assert sink.pending == 3
    assert table.current() is None, "nothing is committed until it is flushed"

    sink.flush()

    assert sink.pending == 0
    assert table.snapshot_ids() == (1,)
    assert len(read_bars(table)) == 3


@pytest.mark.trace("REQ-TBL-001")
def test_flushing_nothing_commits_nothing(table: Table) -> None:
    """A snapshot identical to its parent under a new id would make every
    consumer keyed by snapshot see a change that did not happen."""
    sink = BarSink(table=table)

    assert sink.flush() is None
    assert table.snapshot_ids() == ()


@pytest.mark.trace("REQ-TBL-001")
def test_the_sink_is_the_builder_s_own_hook() -> None:
    """`BarBuilder.on_final` fires when a window closes and never again for that
    window ([[ADR-005]]), which is exactly the moment a canonical table may have
    the row."""
    store = InMemoryObjectStore()
    table = table_for(store)
    sink = BarSink(table=table)
    builder = BarBuilder(timeframe_ns=MINUTE_NS, on_final=sink)

    assert builder.on_final is sink

    sink(bar(1))
    sink.flush()

    assert read_bars(table) == [bar(1)]


@pytest.mark.trace("REQ-TBL-001")
def test_the_table_keeps_the_plane_s_own_guarantees(table: Table) -> None:
    """It is a lakehouse table, so its history is immutable and every snapshot
    has an identity -- which is what makes a backfill re-runnable and a research
    read pinnable."""
    first = write_bars(table, [bar(1)])
    write_bars(table, [bar(2)])

    assert table.snapshot(1).content_hash == first
    assert len(read_bars(table, snapshot_id=1)) == 1
    assert len(read_bars(table)) == 2


@pytest.mark.trace("REQ-TBL-001")
def test_a_row_carries_every_field_of_a_bar() -> None:
    """A field the schema forgot is a field that reads back as a default, and a
    default in a canonical table is a value nobody wrote."""
    row = to_row(bar(1))

    assert set(row) == set(SCHEMA.names)
    assert set(Bar.model_fields) - set(row) == {"is_final"}


@pytest.mark.trace("REQ-TBL-001")
def test_a_row_round_trips_through_the_reader_alone() -> None:
    original = bar(7)

    assert from_row(to_row(original)) == original
