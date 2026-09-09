"""Bounded research extracts through DuckDB.

REQ-STORE-001, PRD §29.0: "query Iceberg with Trino or bounded extracts with
DuckDB".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.lakehouse import (
    InMemoryObjectStore,
    SnapshotEmpty,
    Table,
    extract,
    query,
    snapshot_of,
)

from .conftest import trade


@pytest.mark.trace("REQ-STORE-001")
def test_a_snapshot_is_queryable_by_the_table_s_own_name(trades: Table) -> None:
    trades.append([trade(1, symbol="BTCUSDT"), trade(2, symbol="ETHUSDT"), trade(3)])

    rows = query(trades, 'SELECT symbol, count(*) AS n FROM "cex_trades" GROUP BY 1 ORDER BY 1')

    assert rows.to_pylist() == [
        {"symbol": "BTCUSDT", "n": 2},
        {"symbol": "ETHUSDT", "n": 1},
    ]


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_at_an_older_snapshot_sees_that_snapshot(trades: Table) -> None:
    """A research result pinned to a dataset has to keep matching it."""
    trades.append([trade(1)])
    trades.append([trade(2), trade(3)])

    assert query(trades, 'SELECT count(*) AS n FROM "cex_trades"', snapshot_id=1).to_pylist() == [
        {"n": 1}
    ]
    assert query(trades, 'SELECT count(*) AS n FROM "cex_trades"').to_pylist() == [{"n": 3}]


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_sees_only_the_files_the_manifest_names(
    trades: Table, store: InMemoryObjectStore
) -> None:
    """The reason the extract goes through the port rather than through an
    `s3://` glob.

    A glob reads whatever is under a prefix at the moment it runs -- orphans
    from a lost commit included. That is a different question with the same
    shape, which is the kind of difference nobody notices in a result.
    """
    trades.append([trade(1)])
    orphan = Table(name="cex_trades", schema=trades.schema, store=InMemoryObjectStore())
    orphan.append([trade(99)])
    for key in orphan.store.list("cex_trades/data/"):  # type: ignore[attr-defined]
        store.put(key.replace("/00000001/", "/00000009/"), orphan.store.get(key))  # type: ignore[attr-defined]

    assert len(store.list("cex_trades/data/")) == 2, "the orphan is really in the store"
    assert query(trades, 'SELECT count(*) AS n FROM "cex_trades"').to_pylist() == [{"n": 1}]


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_over_a_table_with_no_snapshot_is_refused(trades: Table) -> None:
    """An empty result reads like a finding."""
    with pytest.raises(SnapshotEmpty, match="reads like a finding"):
        query(trades, 'SELECT * FROM "cex_trades"')


@pytest.mark.trace("REQ-STORE-001")
def test_the_extract_does_not_outlive_the_query(trades: Table) -> None:
    """Leaving files behind would create a second copy of the canonical plane
    that nothing tracks, and the first stale read from it would look exactly
    like a correct one."""
    trades.append([trade(1)])

    with extract(trades) as paths:
        assert paths and all(path.exists() for path in paths)
        directory = paths[0].parent

    assert not Path(directory).exists()


@pytest.mark.trace("REQ-STORE-001")
def test_a_result_can_name_the_dataset_it_read(trades: Table) -> None:
    """PRD §0 item 13's first hash: a research run records which dataset it saw
    by content, not by a path that may hold something else later."""
    first = trades.append([trade(1)])
    trades.append([trade(2)])

    assert snapshot_of(trades, 1).content_hash == first.content_hash
    assert snapshot_of(trades).content_hash != first.content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_a_query_reads_every_file_a_snapshot_names(trades: Table) -> None:
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
