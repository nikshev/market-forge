"""The canonical plane on Apache Iceberg.

# @trace: REQ-WP-039
# @trace: REQ-STORE-001
# @trace: REQ-WP-041

[[ADR-002]] chose "Parquet on S3-compatible object storage with Iceberg table
semantics"; `table.py` implements those semantics by hand and [[ADR-060]]
records why the approximation is being replaced. The short version: that table
can only append, so nothing it offers makes a data file unreferenced, so
retention has nothing to free. Iceberg has the missing operation.

**A point-in-time read composes two dimensions.** PRD Principle I asks for "data
with `event_time <= t` that was actually available then", and those are
different questions whenever a commit backfills rows older than its
predecessor -- which every replay does. Measured:

    commit 1: event times 100, 200
    commit 2: event times  10,  20     (a backfill)

    by snapshot 1    -> 100, 200
    by filter <= 200 -> 10, 20, 100, 200

The snapshot is what was known; the filter is what had happened. `read` takes
both, as the hand-rolled one already did.

**Identity stays ours** ([[ADR-053]]). Iceberg allocates snapshot ids, so two
runs over identical data get different ones, and PRD §0 item 13's
reproducibility claim rests on a hash of the rows. It is computed here, over the
rows a snapshot can see, in the schema's own canonical encoding -- which makes
it independent of the writer, of the file layout, and of how many commits the
rows arrived in.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

import pyarrow as pa
import pyarrow.compute as pc
from pyiceberg.catalog import Catalog as Catalog
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError, NoSuchTableError
from pyiceberg.table import Table as _IcebergTable

from channelflow.lakehouse.schema import Schema

#: One namespace for the whole plane. Tables are named by the domain, and a
#: second level of naming would be a place for two tables to disagree about
#: which one is canonical.
NAMESPACE = "channelflow"


class NoEventTime(ValueError):
    """A point-in-time read was asked of a table that has no event time.

    Refused rather than answered with everything: returning every row would
    answer a different question in a way the caller could not detect.
    """


class NoSuchSnapshot(LookupError):
    """A snapshot the table does not have."""


class EmptyAppend(ValueError):
    """A commit that adds nothing.

    Refused rather than recorded: a snapshot with no rows says something
    happened, and every reader downstream would believe it.
    """


def catalog(*, uri: str, warehouse: str, **properties: str) -> Catalog:
    """The catalog, wherever it lives.

    A SQLite URI and a local directory for tests and the fast gate; a PostgreSQL
    URI and an S3 warehouse elsewhere. One implementation, two URLs -- which is
    the line [[ADR-002]] drew between a test double and a second production
    path, and what keeps REQ-INFRA-002's "a commit needs no running service"
    true.

    **Nothing here branches on the scheme**, and a test reads this function to
    check that ([[REQ-WP-041]]). A catalog that reached PostgreSQL through a
    second path would pass every behavioural test and be the second production
    path [[ADR-002]] refused.

    `properties` is what the storage needs -- an endpoint and credentials for
    S3, nothing for a local directory. It is passed through rather than
    interpreted: the moment this function knew what an `s3.endpoint` was, it
    would be the place a second backend's options went too.
    """
    store = SqlCatalog("channelflow", uri=uri, warehouse=_as_location(warehouse), **properties)
    try:
        store.create_namespace(NAMESPACE)
    except NamespaceAlreadyExistsError:
        pass
    return store


def _as_location(warehouse: str) -> str:
    if "://" in warehouse:
        return warehouse
    return f"file://{warehouse}"


@dataclass(frozen=True)
class TableSnapshot:
    """One commit, named the way this system names things.

    `snapshot_id` is ours -- small and sequential, because every caller in the
    domain uses `1, 2, 3` and none of them should learn what Iceberg is.
    `iceberg_id` is the allocated one, kept for anything that has to talk to the
    format directly.
    """

    snapshot_id: int
    iceberg_id: int
    parent_id: int | None
    record_count: int
    #: The latest event time among the rows visible at this commit. Not a commit
    #: time: nothing here reads a clock.
    event_time_max_ns: int
    #: Over the rows, in the schema's canonical encoding ([[ADR-053]]).
    content_hash: str


class IcebergTable:
    """A named, schema'd, append-only dataset with a readable history."""

    def __init__(self, *, name: str, schema: Schema, catalog: Catalog) -> None:
        self.name = name
        self.schema = schema
        self.catalog = catalog

    # --- reading -----------------------------------------------------------

    def handle(self) -> _IcebergTable | None:
        """The Iceberg table itself, for the one caller that needs its layout.

        Backup has to walk manifests and metadata, which is knowledge about the
        format rather than about the data. Exposing it here, once and named, is
        better than a second module learning to load tables.
        """
        return self._table()

    def snapshot_ids(self) -> tuple[int, ...]:
        """Every committed snapshot, oldest first, by sequence number.

        **Not by position.** Expiring a snapshot renumbers positions, so a run
        that recorded "snapshot 3" would resolve to a different dataset after a
        retention pass and nothing would say so -- which would make PRD §0 item
        13's reproducibility claim quietly untrue. Iceberg's sequence numbers
        survive expiry: measured, a table whose first two snapshots are expired
        keeps 3 and 4 as 3 and 4.

        A fresh table still counts 1, 2, 3, because sequence numbers start at
        one and rise by one per commit.
        """
        table = self._table()
        if table is None:
            return ()
        return tuple(sorted(int(s.sequence_number or 0) for s in table.metadata.snapshots))

    def snapshot(self, snapshot_id: int) -> TableSnapshot:
        if snapshot_id not in self.snapshot_ids():
            raise NoSuchSnapshot(
                f"{self.name} has no snapshot {snapshot_id}; it has {self.snapshot_ids() or 'none'}"
            )
        return self._describe(snapshot_id)

    def current(self) -> TableSnapshot | None:
        """The newest snapshot, or `None` for a table nothing has committed to.

        `None` rather than an empty snapshot: a table nobody has written to and
        one whose latest commit holds no rows are different facts -- and the
        second cannot exist here, because an empty append is refused.
        """
        ids = self.snapshot_ids()
        return self._describe(ids[-1]) if ids else None

    def read(self, *, snapshot_id: int | None = None, as_of_ns: int | None = None) -> pa.Table:
        """The rows of a snapshot, optionally as of an instant.

        Two dimensions, composed. `snapshot_id` is what was known; `as_of_ns` is
        what had happened. Either alone answers a different question, and on a
        backfill the difference is the look-ahead Principle I forbids.
        """
        table = self._table()
        if table is None:
            return self.schema.arrow().empty_table()

        ids = self.snapshot_ids()
        if snapshot_id is None:
            if not ids:
                return self.schema.arrow().empty_table()
            wanted = ids[-1]
        else:
            wanted = snapshot_id
        rows = self._in_commit_order(table, wanted)

        if as_of_ns is None:
            return rows

        column = self.schema.event_time_column
        if column is None:
            raise NoEventTime(
                f"{self.name} declares no event-time column, so it cannot answer a "
                "point-in-time read. Returning everything would answer a different "
                "question in a way the caller could not detect"
            )
        return rows.filter(pc.less_equal(rows[column], pa.scalar(as_of_ns, pa.int64())))

    def _in_commit_order(self, table: _IcebergTable, snapshot_id: int) -> pa.Table:
        """Rows oldest commit first, within a commit in the order written.

        Iceberg's own scan returns the newest manifest first -- measured, and
        the reverse of what the plane this replaces guaranteed. That guarantee
        is load-bearing: every "latest row wins" reader in the API folds rows in
        order and would silently start returning the *oldest* value for each
        key, and reversed rows are still rows.

        The order comes from the sequence number Iceberg records against each
        data file, not from walking the snapshot chain. An earlier version
        walked the chain and took each file at its first appearance, which was
        correct until retention expired a link: with the older snapshots gone
        there was nothing left to say which file came first, and a pinned
        snapshot read back in a different order than it was written. The
        sequence numbers survive expiry, so they do not lose that.
        """
        target = self._allocated(table, snapshot_id)
        snapshot = next(s for s in table.metadata.snapshots if int(s.snapshot_id) == target)
        ordered: list[tuple[int, str]] = []
        seen: set[str] = set()
        for manifest in snapshot.manifests(table.io):
            # Live entries only: a manifest keeps a record of files the table
            # has dropped, and reading those would return rows a delete removed.
            # An earlier version also intersected this with `plan_files`, which
            # asks the same question a second way -- the mutation sweep found
            # that second filter unreachable, so it is gone along with the extra
            # scan it cost.
            for entry in manifest.fetch_manifest_entry(table.io):
                path = entry.data_file.file_path
                if path not in seen:
                    seen.add(path)
                    ordered.append((int(entry.sequence_number or 0), path))
        if not ordered:
            return self.schema.arrow().empty_table()

        import pyarrow.parquet as pq

        pieces = [
            pq.read_table(table.io.new_input(path).open()).cast(self.schema.arrow())
            for _, path in sorted(ordered)
        ]
        return pa.concat_tables(pieces)

    # --- appending ---------------------------------------------------------

    def append(self, rows: Sequence[Mapping[str, object]]) -> TableSnapshot:
        """Write `rows` as one commit.

        Concurrency is Iceberg's: a writer whose parent moved retries and lands.
        The hand-rolled layer refused the loser, and measuring that against this
        showed the refusal for what it was -- a dropped write in a path that
        ingests concurrently, which is a defect rather than a guarantee.
        """
        if not rows:
            raise EmptyAppend(
                f"an append of no rows to {self.name} would commit a snapshot saying "
                "something happened"
            )
        table = self._table() or self.catalog.create_table(
            f"{NAMESPACE}.{self.name}", schema=self.schema.arrow()
        )
        table.append(self._arrow(rows))
        return self._describe(self.snapshot_ids()[-1])

    # --- what retention needs ----------------------------------------------

    def delete_rows_before(self, event_time_ns: int) -> None:
        """Drop rows older than an instant.

        The operation the hand-rolled plane does not have. It rewrites the live
        file set: files whose rows all match are dropped, and one that straddles
        the boundary is rewritten copy-on-write. Either way the originals stop
        being referenced, which is the thing retention needs and appending can
        never produce.
        """
        column = self.schema.event_time_column
        if column is None:
            raise NoEventTime(
                f"{self.name} declares no event-time column, so it has no notion of "
                "rows being old enough to drop"
            )
        table = self._table()
        if table is None:
            return
        table.delete(f"{column} < {event_time_ns}")

    def expire_snapshots_except(self, keep: Sequence[int]) -> None:
        """Forget every snapshot but these.

        On its own this frees nothing -- measured, and the correction
        [[ADR-060]] carries. It removes the references that survived a delete,
        so that what the delete unreferenced is unreferenced by everything.
        """
        from pyiceberg.table.maintenance import MaintenanceTable

        table = self._require_table()
        kept = set(keep)
        doomed = [
            snapshot.snapshot_id
            for snapshot in table.metadata.snapshots
            if int(snapshot.sequence_number or 0) not in kept
        ]
        if not doomed:
            return
        MaintenanceTable(table).expire_snapshots().by_ids(doomed).commit()

    def expire_snapshots_before(self, snapshot_id: int) -> None:
        """Forget the history older than a snapshot.

        On its own this frees nothing -- measured, and the correction that
        [[ADR-060]] carries. It removes the references that survived a delete,
        so that what the delete unreferenced is unreferenced by everything.
        """
        from pyiceberg.table.maintenance import MaintenanceTable

        table = self._require_table()
        older = [
            snapshot.snapshot_id
            for snapshot in table.metadata.snapshots
            if int(snapshot.sequence_number or 0) < snapshot_id
        ]
        if not older:
            return
        MaintenanceTable(table).expire_snapshots().by_ids(older).commit()

    def unreferenced_files(self) -> tuple[str, ...]:
        """Data files no live snapshot plans.

        Exactly what retention may remove, and nothing else. Produced here
        rather than in `retention.py` so that knowledge of Iceberg's layout
        lives in one module.
        """
        table = self._table()
        if table is None:
            return ()
        live = {
            task.file.file_path
            for snapshot in table.metadata.snapshots
            for task in table.scan(snapshot_id=snapshot.snapshot_id).plan_files()
        }
        on_disk = {entry for entry in _walk(table.location()) if entry.endswith(".parquet")}
        return tuple(
            sorted(path for path in on_disk if _strip(path) not in {_strip(f) for f in live})
        )

    # --- internals ---------------------------------------------------------

    def _table(self) -> _IcebergTable | None:
        try:
            return self.catalog.load_table(f"{NAMESPACE}.{self.name}")
        except NoSuchTableError:
            return None

    def _require_table(self) -> _IcebergTable:
        table = self._table()
        if table is None:
            raise NoSuchSnapshot(f"{self.name} has no snapshots; nothing has been committed")
        return table

    def _allocated(self, table: _IcebergTable, snapshot_id: int) -> int:
        """Iceberg's own id for the snapshot this system calls `snapshot_id`."""
        for snapshot in table.metadata.snapshots:
            if int(snapshot.sequence_number or 0) == snapshot_id:
                return int(snapshot.snapshot_id)
        raise NoSuchSnapshot(
            f"{self.name} has no snapshot {snapshot_id}; it has {self.snapshot_ids() or 'none'}"
        )

    def _describe(self, snapshot_id: int) -> TableSnapshot:
        table = self._require_table()
        iceberg = next(
            s for s in table.metadata.snapshots if int(s.sequence_number or 0) == snapshot_id
        )
        earlier = [i for i in self.snapshot_ids() if i < snapshot_id]
        rows = self.read(snapshot_id=snapshot_id)
        column = self.schema.event_time_column
        return TableSnapshot(
            snapshot_id=snapshot_id,
            iceberg_id=int(iceberg.snapshot_id),
            parent_id=earlier[-1] if earlier else None,
            record_count=rows.num_rows,
            event_time_max_ns=(
                int(pc.max(rows[column]).as_py() or 0) if column and rows.num_rows else 0
            ),
            content_hash=self._content_hash(rows),
        )

    def _content_hash(self, rows: pa.Table) -> str:
        """[[ADR-053]]'s identity, over rows rather than bytes.

        The encodings are sorted before digesting, so a dataset's identity does
        not depend on which file a row landed in or how many commits carried it
        -- two facts about a writer, not about the data.
        """
        encoded = sorted(self.schema.encode_row(self._to_domain(row)) for row in rows.to_pylist())
        digest = hashlib.sha256()
        for line in encoded:
            digest.update(line)
        return digest.hexdigest()

    def _to_domain(self, row: Mapping[str, object]) -> dict[str, object]:
        """A stored row back in the shapes the schema's encoder expects.

        The inverse of the conversion on the way in. It exists so the canonical
        encoder stays the single definition of what a row *is*: hashing storage
        shapes instead would work and would put a second canonicalisation in the
        codebase, and two canonical forms drift.
        """
        out: dict[str, object] = {}
        for column in self.schema.columns:
            value = row[column.name]
            if column.type == "decimal":
                out[column.name] = None if value is None else Decimal(str(value))
            elif column.type == "float_map":
                out[column.name] = None if value is None else dict(value)  # type: ignore[call-overload]
            else:
                out[column.name] = value
        return out

    def _arrow(self, rows: Sequence[Mapping[str, object]]) -> pa.Table:
        """Rows in the shape Arrow wants.

        The conversion happens here rather than in the caller, as it did in the
        layer this replaces: a table that took storage shapes would push the
        round trip onto every producer, and one of them would store a price as a
        float by accident.
        """
        columns = {
            column.name: [_for_arrow(column.type, row[column.name]) for row in rows]
            for column in self.schema.columns
        }
        return pa.table(columns, schema=self.schema.arrow())


def _for_arrow(column_type: str, value: object) -> object:
    """One value in the shape Arrow wants for its column type.

    Decimals become their exact text and maps become pair lists, here rather
    than in the caller: a table that took the storage shapes would push the
    conversion onto every producer, and one of them would store a float by
    accident.
    """
    if value is None:
        # Arrow stores a real null. Stringifying it first put the literal text
        # "None" in a decimal column, which read back as a `Decimal("None")` --
        # and which anything reading the Parquet directly, as PRD section 6.4
        # plans for with Trino and DuckDB, would have seen as that text.
        return None
    if column_type == "decimal":
        return str(value)
    if column_type == "float_map":
        assert isinstance(value, Mapping)
        return [(key, value[key]) for key in sorted(value)]
    return value


def _walk(location: str) -> list[str]:
    from pathlib import Path

    root = location.removeprefix("file://")
    if not Path(root).is_dir():
        return []
    return [str(path) for path in Path(root).rglob("*") if path.is_file()]


def _strip(path: str) -> str:
    return path.removeprefix("file://")
