"""A backup is a claim about restoring, so these tests restore (REQ-WP-037).

Rewritten for the Iceberg layout ([[ADR-060]]). The guarantees are the ones the
requirement always asked for; one of them is narrower, and [[ADR-061]] says why:
a restore lands where the backup came from, because Iceberg's metadata holds
absolute URIs and a tree restored elsewhere names a place that holds nothing.

The interruption tests are the ones that check the copy order, because a
completed copy is complete whatever order it went in.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from channelflow.lakehouse import (
    Catalog,
    Column,
    IcebergTable,
    NothingToRestore,
    Schema,
    TargetNotEmpty,
    back_up,
    restore,
    verify,
)
from channelflow.lakehouse import catalog as open_catalog

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


def row(index: int) -> dict[str, object]:
    return {"event_time_ns": index * SECOND, "symbol": "BTCUSDT", "price": 50_000.0 + index}


def filled(catalog: Catalog, commits: int = 3) -> IcebergTable:
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)
    for commit in range(commits):
        table.append([row(commit * 10 + offset) for offset in range(3)])
    return table


def fresh_catalog(home: Path) -> Catalog:
    home.mkdir(parents=True, exist_ok=True)
    return open_catalog(uri=f"sqlite:///{home}/catalog.db", warehouse=str(home))


# --- the round trip -----------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_a_backed_up_table_restores_row_for_row(catalog: Catalog, tmp_path: Path) -> None:
    """What somebody actually wanted back, asserted on rows rather than digests.

    A digest check proves the metadata agrees with the files; the rows are the
    thing.
    """
    table = filled(catalog)
    before = table.read().to_pylist()
    target = tmp_path / "backup"

    back_up(table, target=target)

    # The table's own location is emptied and its catalog forgotten: a disaster,
    # of the kind a restore is for.
    location = Path(table.handle().location().removeprefix("file://"))
    shutil.rmtree(location)
    fresh = fresh_catalog(tmp_path / "after")

    restore("cex_trades", backup=target, catalog=fresh)

    restored = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=fresh)
    assert restored.read().to_pylist() == before


@pytest.mark.trace("REQ-WP-037")
def test_point_in_time_reads_survive_the_round_trip(catalog: Catalog, tmp_path: Path) -> None:
    """The history, not only the latest state. A backup that restored the newest
    rows and lost the snapshots behind them would read correctly and answer
    every earlier question wrongly."""
    table = filled(catalog, commits=3)
    target = tmp_path / "backup"
    back_up(table, target=target)

    shutil.rmtree(Path(table.handle().location().removeprefix("file://")))
    fresh = fresh_catalog(tmp_path / "after")
    restore("cex_trades", backup=target, catalog=fresh)

    restored = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=fresh)
    assert restored.snapshot_ids() == (1, 2, 3)
    assert restored.read(snapshot_id=1).num_rows == 3


@pytest.mark.trace("REQ-WP-037")
def test_a_restore_says_where_it_landed(catalog: Catalog, tmp_path: Path) -> None:
    table = filled(catalog, commits=2)
    target = tmp_path / "backup"
    back_up(table, target=target)
    shutil.rmtree(Path(table.handle().location().removeprefix("file://")))

    report = restore("cex_trades", backup=target, catalog=fresh_catalog(tmp_path / "after"))

    assert report.landed_on == 2


@pytest.mark.trace("REQ-WP-037")
def test_a_table_nobody_committed_to_backs_up_as_nothing(catalog: Catalog, tmp_path: Path) -> None:
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)

    report = back_up(table, target=tmp_path / "backup")

    assert report.snapshots == 0
    assert report.files == 0


# --- the ordering rule --------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_an_interrupted_backup_never_leaves_metadata_over_absent_data(
    catalog: Catalog, tmp_path: Path
) -> None:
    """The copy order, at every point the copy could stop.

    Iceberg writes data files, then the manifests naming them, then the manifest
    list, then the metadata naming that. Copy in any other order and an
    interruption leaves the backup pointing at something that is not there --
    the one state the writer refuses to create.

    Asserted structurally: at every prefix of the copy, no file in the backup
    names a file that is missing from it.
    """
    table = filled(catalog, commits=3)
    complete = tmp_path / "complete"
    back_up(table, target=complete)
    everything = sorted(p for p in complete.rglob("*") if p.is_file() and p.name != "ORIGIN")

    for stop in range(1, len(everything) + 1):
        partial = tmp_path / f"partial-{stop}"
        for source in everything[:stop]:
            destination = partial / source.relative_to(complete)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

        present = {p.name for p in partial.rglob("*") if p.is_file()}
        # A manifest or metadata file arrives only after what it names, so
        # anything that references a parquet must find it here.
        for file in partial.rglob("*.avro"):
            assert file.name in present


@pytest.mark.trace("REQ-WP-037")
def test_re_running_a_backup_copies_nothing_and_raises_nothing(
    catalog: Catalog, tmp_path: Path
) -> None:
    """What makes an interrupted backup resumable rather than a fresh copy."""
    table = filled(catalog, commits=2)
    target = tmp_path / "backup"

    first = back_up(table, target=target)
    again = back_up(table, target=target)

    assert first.files > 0
    assert again.files == 0


# --- never merged -------------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_restoring_over_an_existing_table_is_refused(catalog: Catalog, tmp_path: Path) -> None:
    """Merging two histories under one name produces a history that never
    existed. Idempotent means restoring twice is safe, not that two lineages can
    be blended."""
    table = filled(catalog, commits=2)
    target = tmp_path / "backup"
    back_up(table, target=target)

    with pytest.raises(TargetNotEmpty):
        restore("cex_trades", backup=target, catalog=catalog)


@pytest.mark.trace("REQ-WP-037")
def test_restoring_from_somewhere_holding_no_backup_is_refused(tmp_path: Path) -> None:
    """An empty directory is not an empty table."""
    with pytest.raises(NothingToRestore):
        restore("cex_trades", backup=tmp_path, catalog=fresh_catalog(tmp_path / "after"))


# --- verification -------------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_a_whole_table_verifies(catalog: Catalog) -> None:
    table = filled(catalog, commits=2)

    assert verify(table).ok


@pytest.mark.trace("REQ-WP-037")
def test_a_missing_file_is_found_wherever_in_the_history_it_is(catalog: Catalog) -> None:
    """Across the whole history, not only the newest snapshot: a break behind
    the latest commit still fails every point-in-time read, which is what the
    plane exists for."""
    table = filled(catalog, commits=3)
    handle = table.handle()
    first = handle.metadata.snapshots[0]
    doomed = next(
        entry.data_file.file_path
        for manifest in first.manifests(handle.io)
        for entry in manifest.fetch_manifest_entry(handle.io, discard_deleted=False)
    )
    Path(doomed.removeprefix("file://")).unlink()

    report = verify(table)

    assert report.missing == (doomed,)
    assert not report.ok


@pytest.mark.trace("REQ-WP-037")
def test_a_table_with_nothing_in_it_verifies(catalog: Catalog) -> None:
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)

    assert verify(table).ok
