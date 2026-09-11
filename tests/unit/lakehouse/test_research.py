"""Bounded research extracts through DuckDB.

REQ-STORE-001, PRD §29.0: "query Iceberg with Trino or bounded extracts with
DuckDB".
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from channelflow.lakehouse import (
    IcebergTable,
    SnapshotEmpty,
    extract,
    query,
    snapshot_of,
)

from .conftest import trade


@pytest.mark.trace("REQ-STORE-001")
def test_a_snapshot_is_queryable_by_the_table_s_own_name(trades: IcebergTable) -> None:
    trades.append([trade(1, symbol="BTCUSDT"), trade(2, symbol="ETHUSDT"), trade(3)])

    rows = query(trades, 'SELECT symbol, count(*) AS n FROM "cex_trades" GROUP BY 1 ORDER BY 1')

    assert rows.to_pylist() == [
        {"symbol": "BTCUSDT", "n": 2},
        {"symbol": "ETHUSDT", "n": 1},
    ]


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_at_an_older_snapshot_sees_that_snapshot(trades: IcebergTable) -> None:
    """A research result pinned to a dataset has to keep matching it."""
    trades.append([trade(1)])
    trades.append([trade(2), trade(3)])

    assert query(trades, 'SELECT count(*) AS n FROM "cex_trades"', snapshot_id=1).to_pylist() == [
        {"n": 1}
    ]
    assert query(trades, 'SELECT count(*) AS n FROM "cex_trades"').to_pylist() == [{"n": 3}]


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_sees_only_the_files_the_snapshot_names(
    trades: IcebergTable, tmp_path: Path
) -> None:
    """The reason the extract goes through the table rather than a glob.

    A glob reads whatever is under a prefix at the moment it runs -- orphans
    from a lost commit, and everything a retention pass has unreferenced but not
    yet removed. That is a different question with the same shape, which is the
    kind of difference nobody notices in a result.

    Rewritten for the Iceberg layout: the orphan is a real parquet file sitting
    in the table's own directory, which is exactly what a retention pass leaves
    behind between its delete and its cleanup.
    """
    import pyarrow.parquet as pq

    trades.append([trade(1)])

    orphan_home = next(tmp_path.rglob("cex_trades/data"), None) or next(
        tmp_path.rglob("cex_trades")
    )
    pq.write_table(
        pa.table(
            {
                "event_time_ns": [99],
                "symbol": ["X"],
                "price": [1.0],
                "size": [1.0],
                "buyer_is_maker": [False],
            }
        ),
        orphan_home / "orphan.parquet",
    )

    assert query(trades, 'SELECT count(*) AS n FROM "cex_trades"').to_pylist() == [{"n": 1}]


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_over_a_table_with_no_snapshot_is_refused(trades: IcebergTable) -> None:
    """An empty result reads like a finding."""
    with pytest.raises(SnapshotEmpty, match="reads like a finding"):
        query(trades, 'SELECT * FROM "cex_trades"')


@pytest.mark.trace("REQ-STORE-001")
def test_the_extract_does_not_outlive_the_query(trades: IcebergTable) -> None:
    """Leaving files behind would create a second copy of the canonical plane
    that nothing tracks, and the first stale read from it would look exactly
    like a correct one."""
    trades.append([trade(1)])

    with extract(trades) as paths:
        assert paths and all(path.exists() for path in paths)
        directory = paths[0].parent

    assert not Path(directory).exists()


@pytest.mark.trace("REQ-STORE-001")
def test_a_result_can_name_the_dataset_it_read(trades: IcebergTable) -> None:
    """PRD §0 item 13's first hash: a research run records which dataset it saw
    by content, not by a path that may hold something else later."""
    first = trades.append([trade(1)])
    trades.append([trade(2)])

    assert snapshot_of(trades, 1).content_hash == first.content_hash
    assert snapshot_of(trades).content_hash != first.content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_reads_every_file_a_snapshot_names(trades: IcebergTable) -> None:
    """A snapshot accumulates its parent's files, so a query over the newest one
    has to open all of them -- a reader that took only the newest file would
    return the last append and look like a working query."""
    trades.append([trade(1)])
    trades.append([trade(2)])
    trades.append([trade(3)])

    rows = query(trades, 'SELECT event_time_ns FROM "cex_trades" ORDER BY 1')

    assert [row["event_time_ns"] for row in rows.to_pylist()] == [
        trade(1)["event_time_ns"],
        trade(2)["event_time_ns"],
        trade(3)["event_time_ns"],
    ]
