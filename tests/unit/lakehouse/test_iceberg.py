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
from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.lakehouse import Catalog, Column, NoEventTime, Schema
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


@pytest.mark.trace("REQ-WP-053")
def test_a_null_is_stored_as_a_null_and_not_as_the_text_none(catalog: Catalog) -> None:
    """Stringifying first put the literal text "None" in a decimal column.

    It read back as `Decimal("None")` and raised, which is the good direction --
    but the file was already wrong, and anything reading the Parquet directly, as
    PRD §6.4 plans for with Trino and DuckDB, would have seen that text where it
    expected a number or a null.
    """
    schema = Schema(
        columns=(
            Column(name="t", type="timestamp_ns"),
            Column(name="price", type="decimal"),
            Column(name="note", type="string"),
        ),
        event_time_column="t",
    )
    table = IcebergTable(name="nullable", schema=schema, catalog=catalog)
    table.append([{"t": 1, "price": None, "note": None}])

    row = table.read().to_pylist()[0]
    assert row["price"] is None
    assert row["note"] is None
    assert row["price"] != "None"


@pytest.mark.trace("REQ-WP-053")
def test_a_null_and_a_value_are_different_datasets(catalog: Catalog) -> None:
    """A price nobody recorded and a price of zero must not share an identity."""
    schema = Schema(
        columns=(Column(name="t", type="timestamp_ns"), Column(name="price", type="decimal")),
        event_time_column="t",
    )
    absent = IcebergTable(name="absent", schema=schema, catalog=catalog)
    zero = IcebergTable(name="zero", schema=schema, catalog=catalog)

    absent_snapshot = absent.append([{"t": 1, "price": None}])
    zero_snapshot = zero.append([{"t": 1, "price": Decimal("0")}])
    assert absent_snapshot.content_hash != zero_snapshot.content_hash


# --------------------------------------------------------------------------
# What a read costs (REQ-WP-068)
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-068")
def test_many_commits_read_back_in_commit_order(catalog: Catalog) -> None:
    """The guarantee the parallel read must not break.

    [[REQ-WP-039]] made commit order load-bearing: every "latest row wins"
    reader folds rows in order, and Iceberg's own scan returns the newest
    manifest first. Concurrency here is only the waiting -- the paths are sorted
    and the pieces concatenated in that order -- and this is what says so.
    """
    table = IcebergTable(
        name="ordered",
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,
    )
    for n in range(40):
        table.append([{"n": n}])

    assert [row["n"] for row in table.read().to_pylist()] == list(range(40))


@pytest.mark.trace("REQ-WP-068")
def test_a_single_file_needs_no_pool(catalog: Catalog) -> None:
    """A pool costs threads and a queue to discover there is nothing to
    parallelise, and most tables in the fast gate hold one commit."""
    table = IcebergTable(
        name="one_file",
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,
    )
    table.append([{"n": 1}, {"n": 2}])

    assert [row["n"] for row in table.read().to_pylist()] == [1, 2]


@pytest.mark.trace("REQ-WP-068")
def test_the_read_concurrency_is_bounded() -> None:
    """Sixteen concurrent requests against a table of many files would otherwise
    open hundreds of connections to one object store."""
    from channelflow.lakehouse.iceberg import READ_WORKERS

    assert 1 < READ_WORKERS <= 32


@pytest.mark.trace("REQ-WP-068")
def test_compaction_keeps_every_row_in_its_order(catalog: Catalog) -> None:
    """The guarantee that makes compaction safe rather than merely faster.

    Measured on a live table of 717 files holding 721 rows: the read that
    followed took 45ms against 6478ms before, and the rows compared equal.
    """
    table = IcebergTable(
        name="fragmented",
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,
    )
    for n in range(30):
        table.append([{"n": n}])
    before = table.read().to_pylist()

    files = table.compact()

    assert files == 30
    assert table.read().to_pylist() == before


@pytest.mark.trace("REQ-WP-068")
def test_compacting_once_is_enough(catalog: Catalog) -> None:
    """A second pass would spend a snapshot saying something happened."""
    table = IcebergTable(
        name="twice",
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,
    )
    for n in range(5):
        table.append([{"n": n}])
    table.compact()
    settled = len(table.snapshot_ids())

    assert table.compact() == 1
    assert len(table.snapshot_ids()) == settled, "a second pass wrote a snapshot"


@pytest.mark.trace("REQ-WP-068")
def test_compacting_a_table_that_does_not_exist_does_nothing(catalog: Catalog) -> None:
    table = IcebergTable(
        name="absent",
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,
    )

    assert table.compact() == 0


# --- compaction while writers are writing (REQ-WP-100) --------------------------------------------


def _numbered(catalog: Catalog, name: str = "busy") -> IcebergTable:
    return IcebergTable(
        name=name,
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,
    )


def _append_during_the_read(table: IcebergTable, writer: IcebergTable, rows: list[int]) -> None:
    """Make another writer commit after `table` has read its files and before it commits."""
    original = table._read_in_order  # noqa: SLF001 -- the seam a concurrent writer lands in
    fired: list[bool] = []

    def read_then_let_a_writer_in(paths, iceberg_table):  # type: ignore[no-untyped-def]
        result = original(paths, iceberg_table)
        if not fired:
            fired.append(True)
            for n in rows:
                writer.append([{"n": n}])
        return result

    table._read_in_order = read_then_let_a_writer_in  # type: ignore[method-assign]  # noqa: SLF001


@pytest.mark.trace("REQ-WP-100")
def test_compaction_survives_a_writer_committing_while_it_runs(catalog: Catalog) -> None:
    """The failure that left a deployment's `bars` table uncompacted for days: compaction reads the
    live rows, takes a minute, and by the time it commits an ingest daemon has appended. It used
    to refuse with `ValidationException` (and, forced through, would have deleted the daemon's
    rows). It must land, and the late rows must still be there."""
    table = _numbered(catalog)
    for n in range(10):
        table.append([{"n": n}])
    _append_during_the_read(table, _numbered(catalog), [100, 101])

    files = table.compact()

    assert files == 10
    assert [r["n"] for r in table.read().to_pylist()] == [*range(10), 100, 101]


@pytest.mark.trace("REQ-WP-100")
def test_a_row_appended_during_compaction_is_not_read_twice(catalog: Catalog) -> None:
    table = _numbered(catalog)
    for n in range(6):
        table.append([{"n": n}])
    _append_during_the_read(table, _numbered(catalog), [50])

    table.compact()

    rows = [r["n"] for r in table.read().to_pylist()]
    assert rows.count(50) == 1
    assert len(rows) == 7


@pytest.mark.trace("REQ-WP-100")
def test_rows_compacted_come_before_rows_a_writer_added_meanwhile(catalog: Catalog) -> None:
    """Every "latest row wins" reader folds rows in commit order. The compacted file is committed
    after the writer's file, so by sequence number alone it would sort after it and the old rows
    would shadow the new: the order has to be kept by what the file replaced."""
    table = _numbered(catalog)
    for n in range(4):
        table.append([{"n": n}])
    _append_during_the_read(table, _numbered(catalog), [900])

    table.compact()
    table.append([{"n": 901}])

    assert [r["n"] for r in table.read().to_pylist()] == [0, 1, 2, 3, 900, 901]


@pytest.mark.trace("REQ-WP-100")
def test_compacting_again_after_a_concurrent_pass_keeps_the_whole_order(catalog: Catalog) -> None:
    table = _numbered(catalog)
    for n in range(4):
        table.append([{"n": n}])
    _append_during_the_read(table, _numbered(catalog), [900])
    table.compact()
    table.append([{"n": 901}])

    table.compact()
    table.append([{"n": 902}])

    assert [r["n"] for r in table.read().to_pylist()] == [0, 1, 2, 3, 900, 901, 902]


@pytest.mark.trace("REQ-WP-100")
def test_the_order_it_keeps_a_file_by_does_not_pile_up_across_passes(catalog: Catalog) -> None:
    table = _numbered(catalog)
    for _ in range(4):
        for n in range(3):
            table.append([{"n": n}])
        table.compact()

    inner = table._table()  # noqa: SLF001
    assert inner is not None
    kept = [k for k in inner.properties if k.startswith("channelflow.sequence.")]

    assert len(kept) == 1, "a property outlives the file it described"


@pytest.mark.trace("REQ-WP-100")
def test_a_table_that_is_compacted_retries_a_lost_commit_more_than_the_default_four_times(
    catalog: Catalog,
) -> None:
    """The first deployed pass gave up after four retries ("branch main has changed") against a
    dozen writers; the retries are cheap, so the table is given many."""
    table = _numbered(catalog)
    for n in range(3):
        table.append([{"n": n}])

    table.compact()

    properties = table._table().properties  # type: ignore[union-attr]  # noqa: SLF001
    assert int(properties["commit.retry.num-retries"]) >= 20
    assert int(properties["commit.retry.max-wait-ms"]) <= 5000


# --- compaction rewrites the tail, not the whole table (REQ-WP-105)
# ---------------------------------


def _files_of(table: IcebergTable) -> list[str]:
    inner = table._table()  # noqa: SLF001
    assert inner is not None
    return sorted(task.file.file_path for task in inner.scan().plan_files())


def _filled(catalog: Catalog, big: int, small: int, name: str = "tail") -> IcebergTable:
    """One commit of `big` rows, then `small` commits of one row each."""
    table = _numbered(catalog, name)
    table.append([{"n": n} for n in range(big)])
    for n in range(small):
        table.append([{"n": 1000 + n}])
    return table


@pytest.mark.trace("REQ-WP-105")
def test_a_large_file_is_left_alone_and_only_the_small_ones_after_it_are_merged(
    catalog: Catalog,
) -> None:
    """Merging the whole table every pass costs what the table holds; merging the tail costs what
    arrived since. On 2026-10-13 the first took 1,612 s for the features table, to fold 68 small
    files into a file of 1.3 million rows that did not need touching."""
    table = _filled(catalog, big=10, small=4)
    (big_file,) = [p for p in _files_of(table)][:1] or [""]
    before = _files_of(table)

    merged = table.compact(big_rows=5)

    after = _files_of(table)
    assert merged == 4
    assert len(after) == 2
    assert set(after) & set(before), "the large file was rewritten"


@pytest.mark.trace("REQ-WP-105")
def test_rows_come_back_in_the_same_order_when_only_the_tail_was_merged(catalog: Catalog) -> None:
    table = _filled(catalog, big=10, small=4)
    expected = [r["n"] for r in table.read().to_pylist()]

    table.compact(big_rows=5)
    table.append([{"n": 2000}])

    assert [r["n"] for r in table.read().to_pylist()] == [*expected, 2000]


@pytest.mark.trace("REQ-WP-105")
def test_a_second_pass_merges_only_what_arrived_since_the_first(catalog: Catalog) -> None:
    # The merged tail is four rows, which is "large" at three: a table whose tail has grown to the
    # size of a large file stops being merged, which is how the cost stays proportional to what
    # arrives.
    table = _filled(catalog, big=10, small=4)
    table.compact(big_rows=3)
    settled = _files_of(table)
    for n in range(3):
        table.append([{"n": 3000 + n}])

    merged = table.compact(big_rows=3)

    assert merged == 3
    assert set(settled) & set(_files_of(table)) == set(settled), "an earlier file was rewritten"


@pytest.mark.trace("REQ-WP-105")
def test_a_table_whose_files_are_all_small_is_merged_whole_as_before(catalog: Catalog) -> None:
    table = _filled(catalog, big=1, small=5)

    assert table.compact(big_rows=5) == 6
    assert len(_files_of(table)) == 1


@pytest.mark.trace("REQ-WP-105")
def test_one_small_file_after_a_large_one_is_not_worth_a_snapshot(catalog: Catalog) -> None:
    table = _filled(catalog, big=10, small=1)
    snapshots = len(table.snapshot_ids())

    assert table.compact(big_rows=5) == 1
    assert len(table.snapshot_ids()) == snapshots


@pytest.mark.trace("REQ-WP-105")
def test_a_small_file_before_a_large_one_is_not_merged_across_it(catalog: Catalog) -> None:
    """Merging it with files after the large one would move rows past it: order is the contract."""
    table = _numbered(catalog, "across")
    table.append([{"n": 1}])
    table.append([{"n": n} for n in range(10, 20)])
    table.append([{"n": 2}])
    table.append([{"n": 3}])
    expected = [r["n"] for r in table.read().to_pylist()]

    table.compact(big_rows=5)

    assert [r["n"] for r in table.read().to_pylist()] == expected
    assert expected == [1, *range(10, 20), 2, 3]


@pytest.mark.trace("REQ-WP-105")
def test_the_default_leaves_a_table_of_a_hundred_thousand_rows_alone() -> None:
    from channelflow.lakehouse.iceberg import BIG_FILE_ROWS

    assert BIG_FILE_ROWS == 100_000
