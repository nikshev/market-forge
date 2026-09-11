"""The canonical plane on Apache Iceberg (REQ-WP-039).

Nine properties the hand-rolled layer guarantees, each with a test, because a
migration does not fail by crashing -- it fails by arriving with a working table
that quietly stopped doing one of them.

No services: the catalog is a SQLite file and the warehouse a temporary
directory, which is the same catalog implementation the stack runs against
PostgreSQL with a different URL ([[ADR-060]]).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from channelflow.lakehouse import Column, NoEventTime, Schema
from channelflow.lakehouse.iceberg import EmptyAppend, IcebergTable, catalog

SECOND = 1_000_000_000


def trades_schema() -> Schema:
    return Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="symbol", type="string"),
            Column(name="price", type="float64"),
        ),
        event_time_column="event_time_ns",
    )


def row(index: int, *, price: float | None = None) -> dict[str, object]:
    return {
        "event_time_ns": index * SECOND,
        "symbol": "BTCUSDT",
        "price": 50_000.0 + index if price is None else price,
    }


@pytest.fixture
def warehouse(tmp_path: Path) -> Iterator[Path]:
    yield tmp_path


@pytest.fixture
def trades(warehouse: Path) -> IcebergTable:
    return IcebergTable(
        name="cex_trades",
        schema=trades_schema(),
        catalog=catalog(uri=f"sqlite:///{warehouse}/catalog.db", warehouse=str(warehouse)),
    )


# --- the past does not change -------------------------------------------------


@pytest.mark.trace("REQ-WP-039")
def test_a_read_at_an_instant_excludes_later_rows(trades: IcebergTable) -> None:
    trades.append([row(1), row(2), row(5)])

    assert trades.read(as_of_ns=2 * SECOND).num_rows == 2


@pytest.mark.trace("REQ-WP-039")
def test_appending_does_not_change_what_an_earlier_read_returned(
    trades: IcebergTable,
) -> None:
    first = trades.append([row(1), row(2)])
    before = trades.read(snapshot_id=first.snapshot_id).num_rows

    trades.append([row(3)])

    assert trades.read(snapshot_id=first.snapshot_id).num_rows == before


@pytest.mark.trace("REQ-WP-039")
def test_a_backfill_is_not_visible_to_an_earlier_read(trades: IcebergTable) -> None:
    """The test that decides how a point-in-time read is built.

    A replay backfills: the second commit carries rows *older* than the first.
    Reading by event time alone would return them for an instant at which nobody
    had them, which is the look-ahead Principle I forbids arriving as a
    correct-looking filter. Reading by snapshot alone would ignore the event
    time. Principle I names both -- "data with `event_time <= t` that was
    actually available then" -- so the read composes them.
    """
    first = trades.append([row(100), row(200)])
    trades.append([row(10), row(20)])

    as_seen_then = trades.read(snapshot_id=first.snapshot_id, as_of_ns=200 * SECOND)

    assert as_seen_then.num_rows == 2
    assert sorted(as_seen_then["event_time_ns"].to_pylist()) == [100 * SECOND, 200 * SECOND]


@pytest.mark.trace("REQ-WP-039")
def test_a_read_by_snapshot_returns_that_commit_s_rows(trades: IcebergTable) -> None:
    first = trades.append([row(1)])
    second = trades.append([row(2)])

    assert trades.read(snapshot_id=first.snapshot_id).num_rows == 1
    assert trades.read(snapshot_id=second.snapshot_id).num_rows == 2


@pytest.mark.trace("REQ-WP-039")
def test_a_read_before_any_data_is_empty_rather_than_an_error(
    trades: IcebergTable,
) -> None:
    """Nothing was knowable then, which is a true answer."""
    trades.append([row(10)])

    assert trades.read(as_of_ns=1).num_rows == 0


# --- commits serialise --------------------------------------------------------


@pytest.mark.trace("REQ-WP-039")
def test_two_writers_from_one_parent_both_land(warehouse: Path) -> None:
    """Corrected against a measurement (see the spec).

    The hand-rolled layer refuses the loser. Iceberg retries and lands it, and
    that is better: refusing a valid append because another writer was faster is
    a dropped write, which in a concurrent ingestion path is a defect wearing a
    guarantee's clothes. What must hold is that commits serialise and nothing is
    ever half-applied.
    """
    cat = catalog(uri=f"sqlite:///{warehouse}/catalog.db", warehouse=str(warehouse))
    one = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=cat)
    other = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=cat)

    one.append([row(1)])
    other.append([row(2)])

    assert one.read().num_rows == 2
    assert one.snapshot_ids() == (1, 2)


@pytest.mark.trace("REQ-WP-039")
def test_an_empty_append_is_refused(trades: IcebergTable) -> None:
    """A commit that adds nothing is a snapshot claiming something happened."""
    with pytest.raises(EmptyAppend):
        trades.append([])


# --- a dataset keeps its name -------------------------------------------------


@pytest.mark.trace("REQ-WP-039")
def test_the_same_rows_hash_the_same_in_two_tables(warehouse: Path, tmp_path: Path) -> None:
    """[[ADR-053]]: identity is over rows, never over bytes.

    Two separate warehouses, two separate catalogs, the same rows.
    """
    other_home = tmp_path / "elsewhere"
    other_home.mkdir()

    here = IcebergTable(
        name="cex_trades",
        schema=trades_schema(),
        catalog=catalog(uri=f"sqlite:///{warehouse}/catalog.db", warehouse=str(warehouse)),
    )
    there = IcebergTable(
        name="cex_trades",
        schema=trades_schema(),
        catalog=catalog(uri=f"sqlite:///{other_home}/catalog.db", warehouse=str(other_home)),
    )

    assert here.append([row(1), row(2)]).content_hash == there.append([row(1), row(2)]).content_hash


@pytest.mark.trace("REQ-WP-039")
def test_the_hash_does_not_depend_on_how_the_rows_were_committed(
    warehouse: Path, tmp_path: Path
) -> None:
    """One commit of two rows and two commits of one row are the same dataset.

    The old format's hash digested per-file digests and would disagree here. The
    rule [[ADR-053]] stated -- identity is the rows -- is what survives, and this
    is where the two readings come apart.
    """
    other_home = tmp_path / "elsewhere"
    other_home.mkdir()
    together = IcebergTable(
        name="cex_trades",
        schema=trades_schema(),
        catalog=catalog(uri=f"sqlite:///{warehouse}/catalog.db", warehouse=str(warehouse)),
    )
    apart = IcebergTable(
        name="cex_trades",
        schema=trades_schema(),
        catalog=catalog(uri=f"sqlite:///{other_home}/catalog.db", warehouse=str(other_home)),
    )

    once = together.append([row(1), row(2)])
    apart.append([row(1)])
    twice = apart.append([row(2)])

    assert once.content_hash == twice.content_hash


@pytest.mark.trace("REQ-WP-039")
def test_different_rows_hash_differently(trades: IcebergTable) -> None:
    first = trades.append([row(1)])
    second = trades.append([row(2)])

    assert first.content_hash != second.content_hash


# --- refusals rather than wrong answers ---------------------------------------


@pytest.mark.trace("REQ-WP-039")
def test_a_point_in_time_read_without_an_event_time_is_refused(warehouse: Path) -> None:
    """Returning everything would answer a different question in a way the
    caller could not detect."""
    config = IcebergTable(
        name="market_config",
        schema=Schema(columns=(Column(name="key", type="string"),)),
        catalog=catalog(uri=f"sqlite:///{warehouse}/catalog.db", warehouse=str(warehouse)),
    )
    config.append([{"key": "a"}])

    with pytest.raises(NoEventTime):
        config.read(as_of_ns=1)


@pytest.mark.trace("REQ-WP-039")
def test_a_table_nobody_has_written_to_reports_no_snapshots(trades: IcebergTable) -> None:
    assert trades.snapshot_ids() == ()
    assert trades.current() is None
    assert trades.read().num_rows == 0


# --- what retention will need -------------------------------------------------


@pytest.mark.trace("REQ-WP-039")
def test_nothing_is_unreferenced_in_an_append_only_table(trades: IcebergTable) -> None:
    """The finding that forced this migration, asserted from the other side.

    Appending alone never orphans a file -- which is exactly why the hand-rolled
    plane could not retain anything, and why retention needs a delete.
    """
    trades.append([row(1)])
    trades.append([row(2)])

    assert trades.unreferenced_files() == ()


@pytest.mark.trace("REQ-WP-039")
def test_a_delete_leaves_files_nothing_references(trades: IcebergTable) -> None:
    """The operation the old plane did not have, and the reason for [[ADR-060]].

    After deleting the aged-out rows and expiring the snapshots that still
    pointed at the old files, those files are identifiable -- which is what
    retention removes and all it may remove.
    """
    trades.append([row(1), row(2)])
    trades.append([row(3), row(4)])

    trades.delete_rows_before(3 * SECOND)
    trades.expire_snapshots_before(trades.current().snapshot_id)

    # Which rows survived, not merely how many: a cutoff applied to the wrong
    # side of the comparison also leaves two.
    assert sorted(trades.read()["event_time_ns"].to_pylist()) == [3 * SECOND, 4 * SECOND]
    assert len(trades.unreferenced_files()) > 0


@pytest.mark.trace("REQ-WP-039")
def test_a_delete_alone_frees_nothing_because_the_history_still_points_at_it(
    trades: IcebergTable,
) -> None:
    """The middle link of the chain, and the one that is easy to miss.

    After a delete the current snapshot no longer references the old files --
    but every snapshot before it still does, and they are as live as it is.
    Nothing is removable until that history is expired, which is why retention
    is three operations and not two.
    """
    trades.append([row(1), row(2)])
    trades.append([row(3), row(4)])

    trades.delete_rows_before(3 * SECOND)

    assert trades.unreferenced_files() == ()


@pytest.mark.trace("REQ-WP-039")
def test_the_snapshot_records_what_it_holds(trades: IcebergTable) -> None:
    snapshot = trades.append([row(1), row(5)])

    assert snapshot.record_count == 2
    assert snapshot.event_time_max_ns == 5 * SECOND
    assert snapshot.parent_id is None


@pytest.mark.trace("REQ-WP-039")
def test_rows_come_back_in_commit_order(trades: IcebergTable) -> None:
    """The guarantee nothing had a test for, and the one the migration nearly
    reversed in silence.

    Iceberg's own scan returns the newest manifest first -- measured. The plane
    this replaces returned oldest first, and every "latest row wins" reader in
    the API folds rows in order, so the reversal would have made each of them
    return the *oldest* value for its key. Reversed rows are still rows; nothing
    would have raised.
    """
    trades.append([row(1)])
    trades.append([row(2)])
    trades.append([row(3)])

    assert trades.read()["event_time_ns"].to_pylist() == [1 * SECOND, 2 * SECOND, 3 * SECOND]


@pytest.mark.trace("REQ-WP-039")
def test_order_within_one_commit_is_the_order_written(trades: IcebergTable) -> None:
    trades.append([row(3), row(1), row(2)])

    assert trades.read()["event_time_ns"].to_pylist() == [3 * SECOND, 1 * SECOND, 2 * SECOND]


@pytest.mark.trace("REQ-WP-039")
def test_a_read_does_not_return_rows_a_delete_removed(trades: IcebergTable) -> None:
    """Found by a mutation sweep over retention, and it was the code that was
    wrong.

    The commit order is reconstructed by walking the snapshot chain, and the
    first version took every file any snapshot named. A file a delete drops is
    still named by every earlier snapshot, so the read went on returning rows
    the table no longer held -- correct-looking, and answering a question nobody
    asked. The chain decides the order; the target snapshot decides membership.
    """
    trades.append([row(1), row(2)])
    trades.append([row(3), row(4)])

    trades.delete_rows_before(3 * SECOND)

    assert sorted(trades.read()["event_time_ns"].to_pylist()) == [3 * SECOND, 4 * SECOND]


@pytest.mark.trace("REQ-WP-039")
def test_an_earlier_snapshot_still_sees_what_the_delete_removed(
    trades: IcebergTable,
) -> None:
    """Which is the whole reason the plane keeps a history: the delete is a
    commit, and everything before it is still answerable until retention
    expires it."""
    first = trades.append([row(1), row(2)])
    trades.append([row(3)])

    trades.delete_rows_before(3 * SECOND)

    assert trades.read(snapshot_id=first.snapshot_id).num_rows == 2
