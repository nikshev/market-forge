"""DuckDB over a snapshot's own files.

# @trace: REQ-STORE-001

PRD section 29.0: "**Research:** query Iceberg with Trino or bounded extracts
with DuckDB." This is the second of those, and the word that shapes it is
*bounded*: a query here runs against one snapshot's files, fetched through the
object-store port, and nothing else.

Fetching through the port rather than pointing DuckDB at S3 directly is a
deliberate cost. It means one I/O path instead of two, so an object store the
table layer can read is an object store research can read, and a credential or
an endpoint that works for one works for both. It also means a query cannot
quietly widen its own scope: DuckDB is handed a list of files that a manifest
named, so "which rows did this query see" has the same answer as "what did that
snapshot hold".

The alternative -- `httpfs` and an `s3://` glob -- reads whatever is under a
prefix at the moment it runs, orphaned files from a lost commit included. That
is a different question with the same shape, which is the kind of difference
nobody notices in a result.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from channelflow.lakehouse.iceberg import IcebergTable, TableSnapshot


class SnapshotEmpty(ValueError):
    """A query was asked of a table that has never been committed to."""


@contextmanager
def extract(table: IcebergTable, *, snapshot_id: int | None = None) -> Iterator[list[Path]]:
    """Materialise one snapshot's files locally, and clean up after.

    A context manager because the extract is temporary by design. Leaving files
    behind would create a second copy of the canonical plane that nothing
    tracks, and the first stale read from it would look exactly like a correct
    one.
    """
    if table.current() is None:
        raise SnapshotEmpty(
            f"{table.name} has no snapshot to query; a query over nothing would "
            "return an empty result that reads like a finding"
        )
    rows = table.read(snapshot_id=snapshot_id)
    with tempfile.TemporaryDirectory(prefix="channelflow-extract-") as directory:
        # One file rather than a copy of each of the snapshot's, which is what
        # this did against the layout it replaced. The rows are written in the
        # order `read` guarantees -- oldest commit first -- so a query sees the
        # series the way every other reader does, and DuckDB is handed a file
        # rather than a list whose order it would decide for itself.
        path = Path(directory) / "snapshot.parquet"
        pq.write_table(rows, path)
        yield [path]


def query(
    table: IcebergTable,
    sql: str,
    *,
    snapshot_id: int | None = None,
) -> pa.Table:
    """Run `sql` against one snapshot, which is visible as the table's own name.

    The view carries the table's name so a query reads the way the schema does.
    Nothing else is registered: a query naming a second table is a query this
    function cannot answer, and it says so rather than silently resolving the
    name somewhere else.
    """
    with extract(table, snapshot_id=snapshot_id) as paths:
        connection = duckdb.connect()
        try:
            files = ", ".join(f"'{path}'" for path in paths)
            connection.execute(
                f'CREATE VIEW "{table.name}" AS SELECT * FROM read_parquet([{files}])'
            )
            # `to_arrow_table`, not `arrow()`: the latter hands back a
            # `RecordBatchReader` that is consumed once and is empty on a second
            # read, and this connection is closed on the way out -- so a reader
            # returned from here would be a stream over a closed connection.
            # (`fetch_arrow_table` is the same call under its old name, and
            # DuckDB 1.5 deprecates it.)
            result: pa.Table = connection.execute(sql).to_arrow_table()
            return result
        finally:
            connection.close()


def snapshot_of(table: IcebergTable, snapshot_id: int | None = None) -> TableSnapshot:
    """The snapshot a query would run against, so a result can name its dataset.

    PRD section 0 item 13 wants a result reproducible from a versioned dataset;
    this is how a caller records which one it read, by content hash rather than
    by a path that may hold something else later.
    """
    current = table.current()
    if current is None:
        raise SnapshotEmpty(f"{table.name} has no snapshot")
    return current if snapshot_id is None else table.snapshot(snapshot_id)
