"""The price bins table: written once, read as of an instant, one width at a time (REQ-WP-089)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.tables import volume_bins
from channelflow.volume.bins import BinBlock, BinRow

BLOCK_NS = 300_000_000_000
BASE = 1_788_838_800_000_000_000 // BLOCK_NS * BLOCK_NS


def block(
    i: int, *, width: str = "10", venue: str = "binance", symbol: str = "BTCUSDT", bins=None
) -> BinBlock:
    rows = bins or (
        BinRow(index=10, buy=Decimal("2"), sell=Decimal("1"), unknown=Decimal("0"), trades=3),
        BinRow(index=11, buy=Decimal("4"), sell=Decimal("5"), unknown=Decimal("6"), trades=3),
    )
    return BinBlock(
        venue=venue,
        symbol=symbol,
        block_open_time_ns=BASE + i * BLOCK_NS,
        block_ns=BLOCK_NS,
        bin_width=Decimal(width),
        bins=tuple(rows),
    )


def written(catalog, blocks):
    table = volume_bins.table_for(catalog)
    sink = volume_bins.BinSink(table=table)
    for b in blocks:
        sink(b)
    sink.flush()
    return table


@pytest.mark.trace("REQ-WP-089")
def test_every_bin_of_a_block_is_a_row_and_reads_back_exactly(catalog) -> None:
    table = written(catalog, [block(0)])

    read = volume_bins.read_bins(table, venue="binance", symbol="BTCUSDT")

    assert len(read.rows) == 2
    first = read.rows[0]
    assert (first.bin_index, first.buy, first.sell, first.unknown, first.trades) == (
        10,
        Decimal("2"),
        Decimal("1"),
        Decimal("0"),
        3,
    )
    assert first.block_open_time_ns == BASE
    assert first.bin_width == Decimal("10")


@pytest.mark.trace("REQ-WP-089")
def test_a_read_as_of_an_instant_returns_only_blocks_closed_at_or_before_it(catalog) -> None:
    table = written(catalog, [block(i) for i in range(4)])

    read = volume_bins.read_bins(
        table, venue="binance", symbol="BTCUSDT", as_of_ns=BASE + 2 * BLOCK_NS
    )

    assert {r.block_open_time_ns for r in read.rows} == {BASE, BASE + BLOCK_NS}


@pytest.mark.trace("REQ-WP-089")
def test_a_read_since_an_instant_leaves_out_earlier_blocks(catalog) -> None:
    table = written(catalog, [block(i) for i in range(4)])

    read = volume_bins.read_bins(
        table, venue="binance", symbol="BTCUSDT", since_ns=BASE + 2 * BLOCK_NS
    )

    assert {r.block_open_time_ns for r in read.rows} == {BASE + 2 * BLOCK_NS, BASE + 3 * BLOCK_NS}


@pytest.mark.trace("REQ-WP-089")
def test_rows_of_two_widths_are_never_mixed_the_latest_width_is_used_and_the_rest_are_counted(
    catalog,
) -> None:
    table = written(catalog, [block(0, width="10"), block(1, width="10"), block(2, width="20")])

    read = volume_bins.read_bins(table, venue="binance", symbol="BTCUSDT")

    assert {r.bin_width for r in read.rows} == {Decimal("20")}
    assert read.left_out_rows == 4


@pytest.mark.trace("REQ-WP-089")
def test_series_do_not_see_each_others_rows_and_nothing_gives_an_empty_read(catalog) -> None:
    table = written(catalog, [block(0), block(0, symbol="ETHUSDT")])

    assert len(volume_bins.read_bins(table, venue="binance", symbol="ETHUSDT").rows) == 2
    empty = volume_bins.read_bins(table, venue="bybit", symbol="BTCUSDT")
    assert empty.rows == [] and empty.left_out_rows == 0


@pytest.mark.trace("REQ-WP-089")
def test_the_sink_buffers_until_it_is_flushed_and_flushes_nothing_when_empty(catalog) -> None:
    table = volume_bins.table_for(catalog)
    sink = volume_bins.BinSink(table=table)

    assert sink.flush() is None
    sink(block(0))
    assert sink.pending == 2
    assert volume_bins.read_bins(table, venue="binance", symbol="BTCUSDT").rows == []
    assert sink.flush() is not None
    assert sink.pending == 0
