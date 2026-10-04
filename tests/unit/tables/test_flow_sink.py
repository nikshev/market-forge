"""Flow rows are written once, after the latest on record (REQ-WP-088, ADR-056)."""

from __future__ import annotations

import pytest

from channelflow.features.flow_bars import flow_rows
from channelflow.tables import features as features_table

from ..features.test_flow_bars import make_bar

TIMEFRAME_NS = 60_000_000_000


def stored(table, name="cvd_base"):
    return sorted(row["at_ns"] for row in table.read().to_pylist() if row["feature_name"] == name)


@pytest.mark.trace("REQ-WP-088")
def test_rows_are_written_and_a_second_pass_over_the_same_bars_writes_nothing(catalog) -> None:
    """SC-004."""
    table = features_table.features_table_for(catalog)
    bars = [make_bar(i, str(i + 3), str(7 - i)) for i in range(5)]
    rows = flow_rows(bars, sequential_ids=True)

    first = features_table.write_flow(
        table, venue="binance", symbol="BTCUSDT", timeframe_ns=TIMEFRAME_NS, rows=rows
    )
    second = features_table.write_flow(
        table, venue="binance", symbol="BTCUSDT", timeframe_ns=TIMEFRAME_NS, rows=rows
    )

    assert first == 5
    assert second == 0
    assert stored(table) == [bar.close_time_ns for bar in bars]


@pytest.mark.trace("REQ-WP-088")
def test_a_longer_series_appends_only_what_is_after_the_latest_row(catalog) -> None:
    table = features_table.features_table_for(catalog)
    bars = [make_bar(i, str(i + 3), str(7 - i)) for i in range(6)]

    features_table.write_flow(
        table,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=TIMEFRAME_NS,
        rows=flow_rows(bars[:3], sequential_ids=True),
    )
    written = features_table.write_flow(
        table,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=TIMEFRAME_NS,
        rows=flow_rows(bars, sequential_ids=True),
    )

    assert written == 3
    assert stored(table) == [bar.close_time_ns for bar in bars]


@pytest.mark.trace("REQ-WP-088")
def test_a_shorter_series_writes_nothing_and_never_rewrites(catalog) -> None:
    table = features_table.features_table_for(catalog)
    bars = [make_bar(i, str(i + 3), str(7 - i)) for i in range(5)]
    features_table.write_flow(
        table,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=TIMEFRAME_NS,
        rows=flow_rows(bars, sequential_ids=True),
    )

    written = features_table.write_flow(
        table,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=TIMEFRAME_NS,
        rows=flow_rows(bars[:2], sequential_ids=True),
    )

    assert written == 0
    assert len(stored(table)) == 5


@pytest.mark.trace("REQ-WP-088")
def test_two_series_do_not_see_each_others_latest_row(catalog) -> None:
    table = features_table.features_table_for(catalog)
    bars = [make_bar(i, "5", "3") for i in range(3)]
    rows = flow_rows(bars, sequential_ids=True)

    features_table.write_flow(
        table, venue="binance", symbol="BTCUSDT", timeframe_ns=TIMEFRAME_NS, rows=rows
    )
    other = features_table.write_flow(
        table, venue="binance", symbol="ETHUSDT", timeframe_ns=TIMEFRAME_NS, rows=rows
    )

    assert other == 3
