"""One maintenance pass over a table (REQ-WP-070)."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema, maintenance
from channelflow.lakehouse.retention import RetentionPolicy

SECOND = 1_000_000_000
BASE = 1_700_000_000 * SECOND


def _table(catalog: Catalog, name: str, commits: int = 6) -> IcebergTable:
    table = IcebergTable(
        name=name,
        schema=Schema(
            columns=(Column(name="at_ns", type="timestamp_ns"), Column(name="n", type="int64")),
            event_time_column="at_ns",
        ),
        catalog=catalog,
    )
    for n in range(commits):
        table.append([{"at_ns": BASE + n * SECOND, "n": n}])
    return table


@pytest.mark.trace("REQ-WP-070")
def test_a_pass_compacts_and_reports_what_it_found(catalog: Catalog) -> None:
    table = _table(catalog, "pass_one")
    rows = table.read().to_pylist()

    report = maintenance.run(table)

    assert report.files_before == 6
    assert report.retention is None, "no policy was given, so nothing was expired"
    assert table.read().to_pylist() == rows


@pytest.mark.trace("REQ-WP-070")
def test_compaction_happens_before_retention(catalog: Catalog) -> None:
    """The order is the point. Compaction unreferences the files; retention is
    what removes them. Reversed, retention finds nothing and compaction's output
    waits a whole cycle to be collected."""
    table = _table(catalog, "ordered")

    report = maintenance.run(
        table,
        policy=RetentionPolicy(keep_ns=10_000 * 365 * 24 * 3600 * SECOND),
        now_ns=BASE + 100 * SECOND,
    )

    assert report.files_before == 6
    assert report.retention is not None
    assert report.retention.files_removed == 6, "retention collected what compaction replaced"


@pytest.mark.trace("REQ-WP-070")
def test_a_pass_without_a_policy_expires_nothing(catalog: Catalog) -> None:
    """Expiry is the one operation that destroys, and an operator who wants a
    faster read is not necessarily asking to forget anything."""
    table = _table(catalog, "kept")
    snapshots = len(table.snapshot_ids())

    maintenance.run(table)

    assert len(table.snapshot_ids()) >= snapshots


@pytest.mark.trace("REQ-WP-070")
def test_a_new_table_is_created_already_pruning(catalog: Catalog) -> None:
    """Iceberg keeps every metadata.json unless told not to, and the property is
    off by default — which is why the growth went unnoticed. A table created
    after [[REQ-WP-070]] never accumulates them, so a pass over one has nothing
    to set and says so."""
    table = _table(catalog, "pruned", commits=2)

    assert maintenance.run(table).metadata_pruned is False
    assert table.prune_metadata() is False


@pytest.mark.trace("REQ-WP-070")
def test_a_table_that_predates_the_property_gets_it(catalog: Catalog) -> None:
    """The case the pass exists for: every table written before this kept
    writing a metadata file per commit until somebody said otherwise."""
    from channelflow.lakehouse.iceberg import METADATA_PRUNING, NAMESPACE

    table = _table(catalog, "legacy", commits=2)
    handle = catalog.load_table(f"{NAMESPACE}.legacy")
    with handle.transaction() as transaction:
        transaction.remove_properties(*METADATA_PRUNING)

    assert maintenance.run(table).metadata_pruned is True, "the pass set it"
    assert maintenance.run(table).metadata_pruned is False, "and only once"


@pytest.mark.trace("REQ-WP-070")
def test_the_line_says_what_happened(catalog: Catalog) -> None:
    table = _table(catalog, "reported")

    line = maintenance.run(table).line

    assert "6 file(s) compacted" in line
    assert "metadata pruning already set" in line
