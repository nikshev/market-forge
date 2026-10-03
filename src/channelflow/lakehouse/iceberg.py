"""The canonical plane on Apache Iceberg.

# @trace: REQ-WP-039
# @trace: REQ-STORE-001
# @trace: REQ-WP-041
# @trace: REQ-WP-079

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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock
from typing import Any

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
#: How many data files are opened at once **across every reader in the process**.
#:
#: Measured on a deployment of 685 files: 4394ms serial, 741ms at eight workers,
#: 654ms at sixteen, 605ms at thirty-two.
#:
#: **Shared, not per read.** A per-read pool made one client faster and sixteen
#: clients slower -- 20.2s to 29.1s -- because sixteen requests each opening
#: sixteen files is 256 connections to one object store, which is congestion
#: rather than concurrency. Measured, not reasoned about: the first version was
#: bounded per read and the load test reported the regression ([[REQ-WP-068]]).
READ_WORKERS = 16

#: Iceberg keeps every `metadata.json` it has ever written unless told not to,
#: and each one carries the **full** snapshot list -- so a table committed to N
#: times holds N files whose sizes grow with N.
#:
#: Measured on a deployment after ~900 commits: 2.6 MB of data against **304.9
#: MB of metadata**, a hundred and seventeen times more. Measured again on sixty
#: commits with and without these properties: 61 metadata files and 2020 KiB
#: against 6 and 710 KiB.
#:
#: `delete-after-commit` is off by default, which is the whole reason the growth
#: went unnoticed ([[REQ-WP-070]]). Twenty previous versions is enough to read a
#: table back through a handful of commits and far short of keeping all of them.
METADATA_PRUNING: dict[str, Any] = {
    "write.metadata.delete-after-commit.enabled": "true",
    "write.metadata.previous-versions-max": "20",
}

#: One pool for the process, created on first use. A reader waits for a slot
#: instead of adding a thread, which is the whole point of a shared bound.
_READ_POOL: ThreadPoolExecutor | None = None
_READ_POOL_LOCK = Lock()


def _read_pool() -> ThreadPoolExecutor:
    global _READ_POOL  # noqa: PLW0603 -- one pool per process, by design
    with _READ_POOL_LOCK:
        if _READ_POOL is None:
            _READ_POOL = ThreadPoolExecutor(
                max_workers=READ_WORKERS, thread_name_prefix="lakehouse-read"
            )
        return _READ_POOL


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
        return self._ids_of(table)

    @staticmethod
    def _ids_of(table: _IcebergTable) -> tuple[int, ...]:
        """The snapshot numbers of **one loaded table**, oldest first.

        Every operation that names a snapshot loads the table once and asks it, here, and never
        asks the catalog again ([[REQ-WP-079]]). A second load can hold a commit the first does
        not, and a number taken from one and looked up in the other is the `NoSuchSnapshot` the
        worker and the resample job logged fourteen times in thirteen hours.
        """
        return tuple(sorted(int(s.sequence_number or 0) for s in table.metadata.snapshots))

    def snapshot(self, snapshot_id: int) -> TableSnapshot:
        table = self._table()
        ids = self._ids_of(table) if table is not None else ()
        if table is None or snapshot_id not in ids:
            raise NoSuchSnapshot(
                f"{self.name} has no snapshot {snapshot_id}; it has {ids or 'none'}"
            )
        return self._describe(table, snapshot_id)

    def current(self) -> TableSnapshot | None:
        """The newest snapshot, or `None` for a table nothing has committed to.

        `None` rather than an empty snapshot: a table nobody has written to and
        one whose latest commit holds no rows are different facts -- and the
        second cannot exist here, because an empty append is refused.
        """
        table = self._table()
        if table is None:
            return None
        ids = self._ids_of(table)
        return self._describe(table, ids[-1]) if ids else None

    def read(self, *, snapshot_id: int | None = None, as_of_ns: int | None = None) -> pa.Table:
        """The rows of a snapshot, optionally as of an instant.

        Two dimensions, composed. `snapshot_id` is what was known; `as_of_ns` is
        what had happened. Either alone answers a different question, and on a
        backfill the difference is the look-ahead Principle I forbids.
        """
        table = self._table()
        if table is None:
            return self.schema.arrow().empty_table()

        if snapshot_id is None:
            ids = self._ids_of(table)
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

        return self._read_in_order([path for _, path in sorted(ordered)], table)

    def _read_in_order(self, paths: Sequence[str], table: _IcebergTable) -> pa.Table:
        """Open the data files concurrently and concatenate them in order.

        **Order is preserved by construction**, not by the pool: the paths are
        already sorted by sequence number and the pieces are concatenated in
        that order, so what runs concurrently is only the waiting. Measured on a
        deployment, 685 files: 4394ms serial against 654ms at sixteen workers,
        and the two results compare equal ([[REQ-WP-068]]).

        Serial was never justified -- it was what a comprehension does -- and
        the cost is one round trip to the object store per file, paid one at a
        time. pyiceberg's own `scan().to_arrow()` is concurrent and takes
        1411ms, and is not the answer here because it does not return rows in
        commit order, which [[REQ-WP-039]] made load-bearing.
        """
        import pyarrow.parquet as pq

        schema = self.schema.arrow()

        def one(path: str) -> pa.Table:
            return pq.read_table(table.io.new_input(path).open()).cast(schema)

        # One file needs no pool, and a pool costs threads and a queue to find
        # that out. The bound matters more than the speed-up above it: sixteen
        # concurrent readers of a sixteen-file table would otherwise be 256
        # connections to one object store.
        if len(paths) <= 1:
            return pa.concat_tables([one(path) for path in paths])

        return pa.concat_tables(list(_read_pool().map(one, paths)))

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
        table = self._table()
        if table is None:
            table = self.catalog.create_table(
                f"{NAMESPACE}.{self.name}",
                schema=self.schema.arrow(),
                properties=dict(METADATA_PRUNING),
            )
        table.append(self._arrow(rows))
        # The table object the commit refreshed, not a fresh load: pyiceberg sets
        # `table.metadata` to the commit's own response, so its newest snapshot is the one this
        # call wrote. A new load would name whichever commit is newest by now, which under
        # concurrent writers can be somebody else's, and raise nothing to say so.
        return self._describe(table, self._ids_of(table)[-1])

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

    def prune_metadata(self) -> bool:
        """Ask Iceberg to delete its own superseded metadata from now on.

        Idempotent, and needed on every table created before [[REQ-WP-070]]: the
        properties are set at creation for new ones, and a table that predates
        that keeps writing a file per commit until somebody says otherwise.

        Returns whether anything changed, so a maintenance pass can say it did
        something rather than reporting a success it did not cause.
        """
        table = self._table()
        if table is None:
            return False
        if all(table.properties.get(key) == value for key, value in METADATA_PRUNING.items()):
            return False
        with table.transaction() as transaction:
            transaction.set_properties(**dict(METADATA_PRUNING))
        return True

    def compact(self) -> int:
        """Rewrite the live rows into one file, preserving their order.

        The operation `append` cannot undo. A table written one row at a time
        holds one file per row: measured on a deployment, **685 files for 689
        rows**, each about 8 KiB of Parquet around a few hundred bytes of data,
        and a read that cost 4.4 seconds against §36's two-second budget
        ([[REQ-WP-067]]).

        [[REQ-WP-068]]'s flush policy stops the count growing. It cannot shrink
        one that already grew, and a deployment that ran for a day before the
        fix would otherwise stay slow for as long as it kept its history.

        **Rows come back in commit order and go out in it**, which is what makes
        this safe: `read` already guarantees that order and every "latest row
        wins" reader depends on it, so a compaction that reordered would change
        answers rather than timings. The rewritten file carries them in the same
        sequence, and the old files stop being referenced by the current
        snapshot -- earlier snapshots still name them until they are expired, so
        nothing pinned is lost.

        Returns how many files the live set had before.
        """
        table = self._table()
        if table is None:
            return 0
        before = sum(1 for _ in table.scan().plan_files())
        if before <= 1:
            # Nothing to gain, and an overwrite would spend a snapshot saying
            # something happened.
            return before
        # No empty-table guard: `before > 1` means at least two data files, and
        # Iceberg does not write a file with no rows. The mutation sweep found
        # that branch unreachable, which is what it is for.
        table.overwrite(self.read())
        return before

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
        on_disk = {
            entry for entry in _walk(table.location(), table.io) if entry.endswith(".parquet")
        }
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
            f"{self.name} has no snapshot {snapshot_id}; it has {self._ids_of(table) or 'none'}"
        )

    def _describe(self, table: _IcebergTable, snapshot_id: int) -> TableSnapshot:
        """Describe a snapshot of `table`, using nothing but `table`."""
        iceberg = next(
            s for s in table.metadata.snapshots if int(s.sequence_number or 0) == snapshot_id
        )
        earlier = [i for i in self._ids_of(table) if i < snapshot_id]
        rows = self._in_commit_order(table, snapshot_id)
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


class CannotList(RuntimeError):
    """A location this cannot enumerate.

    Raised rather than answered with an empty list. `unreferenced_files` is what
    [[ADR-062]]'s only deletion asks before it removes anything, and an empty
    answer there means "nothing is orphaned" -- indistinguishable from "I could
    not look". That is what made the walk a no-op on S3 for as long as it was:
    retention expired 933 snapshots and reported freeing zero files, which is
    also what it reports when there is genuinely nothing to free ([[REQ-WP-070]]).
    """


def _walk(location: str, io: object | None = None) -> list[str]:
    """Every file under a location, wherever the location is.

    A local directory for tests and the fast gate, an object store in a
    deployment -- the same line `catalog` draws between one URL and another.
    """
    from pathlib import Path

    if location.startswith(("s3://", "s3a://", "gs://")):
        return _walk_object_store(location, io)

    root = location.removeprefix("file://")
    if not Path(root).is_dir():
        # A local location that is not a directory holds nothing, which is an
        # answer rather than an inability: the directory is created with the
        # first write.
        return []
    return [str(path) for path in Path(root).rglob("*") if path.is_file()]


def _walk_object_store(location: str, io: object | None) -> list[str]:
    """List an object store prefix through the FileIO the table already has.

    Through the table's own `io` rather than a client of this module's making,
    so the credentials and endpoint are the ones the table is already using and
    there is no second place to configure them.
    """
    scheme, _, rest = location.partition("://")
    bucket, _, prefix = rest.partition("/")
    filesystem = getattr(io, "fs_by_scheme", None)
    if filesystem is None:
        raise CannotList(
            f"cannot enumerate {location}: the table's FileIO offers no filesystem, "
            "and an empty answer here would read as 'nothing is orphaned'"
        )
    try:
        from pyarrow.fs import FileSelector

        handle = filesystem(scheme, bucket)
        selector = FileSelector(f"{bucket}/{prefix}".rstrip("/"), recursive=True)
        return [
            f"{scheme}://{info.path}" for info in handle.get_file_info(selector) if info.is_file
        ]
    except CannotList:
        raise
    except Exception as cause:  # noqa: BLE001 -- any failure is an inability to look
        raise CannotList(f"cannot enumerate {location}: {cause}") from cause


def _strip(path: str) -> str:
    return path.removeprefix("file://")
