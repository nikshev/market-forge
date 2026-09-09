"""A table: an append-only chain of snapshots over an object store.

# @trace: REQ-STORE-001

The layout is the whole design, so it is worth reading before the code:

    <table>/metadata/v00000001.json     one manifest per commit, written once
    <table>/data/00000001/<name>.parquet

**There is no current-snapshot pointer.** The current snapshot is the highest
manifest version present, discovered by listing. A pointer would need its own
atomicity and would be one more thing that can disagree with the manifests it
points at; without one, a commit is a single conditional write and the race is
resolved by whoever wins that write.

**Data files are written before the manifest that names them.** A commit that
loses the race leaves those files behind, unreferenced. That is garbage, not
corruption: a reader only ever opens files a manifest lists, so an orphan is
invisible to every query. The alternative -- writing the manifest first --
produces a manifest naming files that may not arrive, which is corruption.

**A snapshot exists exactly when its manifest does.** That is what makes "no
partially written snapshot is readable" true by construction rather than by
care.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from channelflow.lakehouse.schema import Schema
from channelflow.lakehouse.snapshot import DataFile, Snapshot
from channelflow.lakehouse.store import KeyExists, KeyMissing, ObjectStore

#: Parquet writer settings, pinned. They change the bytes a file is made of, so
#: leaving them to the library's defaults would make `file_sha256` depend on a
#: dependency's release notes. They do not affect `content_sha256`, which is the
#: point of [[ADR-053]] -- but a file digest nobody can reproduce is not worth
#: recording either.
COMPRESSION = "zstd"
COMPRESSION_LEVEL = 3

#: Manifest versions are zero-padded to eight digits.
#:
#: Not for correctness: `snapshot_ids` parses each version and sorts the
#: integers, so this code reads the chain correctly whatever order the store
#: lists keys in. A mutation that removed the padding changed no test, which is
#: how that was established rather than assumed.
#:
#: It is kept because the bucket is browsed by people and by tools that do sort
#: lexically -- `aws s3 ls`, a console, a future consumer that takes the last
#: key rather than parsing every one. Padding costs seven characters and removes
#: a trap that only appears at the tenth commit.
VERSION_DIGITS = 8


class SchemaMismatch(ValueError):
    """An append's schema is not the schema the table's history was written with."""


class CommitRaceLost(RuntimeError):
    """Another writer committed this version first."""


class NoSuchSnapshot(LookupError):
    """A read named a snapshot the table does not have."""


class NoEventTime(ValueError):
    """A point-in-time read was asked of a table that has no event time."""


@dataclass(frozen=True)
class Table:
    """One canonical table, over one object store.

    Frozen and stateless: everything about the table lives in the store, so two
    `Table` objects over the same name and store are the same table, and neither
    holds a cached view that could go stale behind the other.
    """

    name: str
    schema: Schema
    store: ObjectStore

    # --- reading the chain -------------------------------------------------

    def _metadata_prefix(self) -> str:
        return f"{self.name}/metadata/"

    def _manifest_key(self, version: int) -> str:
        return f"{self._metadata_prefix()}v{version:0{VERSION_DIGITS}d}.json"

    def snapshot_ids(self) -> tuple[int, ...]:
        """Every committed snapshot, oldest first."""
        prefix = self._metadata_prefix()
        found: list[int] = []
        for key in self.store.list(prefix):
            stem = key[len(prefix) :]
            if not stem.startswith("v") or not stem.endswith(".json"):
                continue
            found.append(int(stem[1:-5]))
        return tuple(sorted(found))

    def snapshot(self, snapshot_id: int) -> Snapshot:
        try:
            raw = self.store.get(self._manifest_key(snapshot_id))
        except KeyMissing as exc:
            raise NoSuchSnapshot(
                f"{self.name} has no snapshot {snapshot_id}; it has {self.snapshot_ids() or 'none'}"
            ) from exc
        return Snapshot.deserialize(raw)

    def current(self) -> Snapshot | None:
        """The newest snapshot, or `None` for a table nothing has committed to.

        `None` rather than an empty snapshot: a table that has never been
        written to and a table whose latest commit holds no rows are different
        facts, and the second one has a content hash.
        """
        ids = self.snapshot_ids()
        return self.snapshot(ids[-1]) if ids else None

    # --- appending ---------------------------------------------------------

    def append(self, rows: Sequence[Mapping[str, object]]) -> Snapshot:
        """Write `rows` as one new file and commit a snapshot naming it.

        Refuses an empty append. Committing a snapshot identical to its parent
        would put a new identity on unchanged data, and every consumer keyed by
        content hash would see a change that did not happen.
        """
        if not rows:
            raise ValueError(
                "an append of no rows would commit a snapshot identical to its "
                "parent under a new id, so anything keyed by snapshot would see a "
                "change that did not happen"
            )

        parent = self.current()
        if parent is not None and parent.schema_fingerprint != self.schema.fingerprint:
            raise SchemaMismatch(
                f"{self.name}'s history was written with schema "
                f"{parent.schema_fingerprint[:12]} and this append carries "
                f"{self.schema.fingerprint[:12]}; an append under a different schema "
                "would put two shapes in one snapshot chain"
            )

        version = (parent.snapshot_id + 1) if parent is not None else 1
        payload, content_hash = self._encode(rows)
        key = f"{self.name}/data/{version:0{VERSION_DIGITS}d}/{content_hash[:16]}.parquet"
        self.store.put(key, payload)

        file = DataFile(
            key=key,
            record_count=len(rows),
            byte_size=len(payload),
            file_sha256=hashlib.sha256(payload).hexdigest(),
            content_sha256=content_hash,
        )
        snapshot = Snapshot(
            snapshot_id=version,
            parent_id=parent.snapshot_id if parent is not None else None,
            schema_fingerprint=self.schema.fingerprint,
            files=(*(parent.files if parent is not None else ()), file),
            # Event time, not wall-clock. A clock reading here would make two
            # replays of the same stream produce different manifests, which is
            # the property Principle XI exists to protect.
            event_time_max_ns=self._latest_event_time(rows, parent),
        )
        try:
            self.store.put_if_absent(self._manifest_key(version), snapshot.serialize())
        except KeyExists as exc:
            raise CommitRaceLost(
                f"{self.name} already has a snapshot {version}; another writer "
                "committed it first. Re-read the table and append again -- the data "
                f"file at {key} is unreferenced and no query can see it"
            ) from exc
        return snapshot

    def _latest_event_time(
        self, rows: Sequence[Mapping[str, object]], parent: Snapshot | None
    ) -> int:
        """The largest event time in this batch, or the parent's for a table
        without one.

        A table with no event-time column has no event time to report, and
        inventing one from a clock is the reading this whole package refuses.
        """
        column = self.schema.event_time_column
        if column is None:
            return parent.event_time_max_ns if parent is not None else 0
        times: list[int] = []
        for row in rows:
            value = row[column]
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{column!r} is the event-time column and this row carries "
                    f"{value!r}; event times are integer nanosecond counts"
                )
            times.append(value)
        return max(times)

    def _encode(self, rows: Sequence[Mapping[str, object]]) -> tuple[bytes, str]:
        """Parquet bytes for these rows, and the digest of their logical content."""
        digest = hashlib.sha256()
        for row in rows:
            digest.update(self.schema.encode_row(dict(row)))

        columns = {
            column.name: [row[column.name] for row in rows] for column in self.schema.columns
        }
        table = pa.table(columns, schema=self.schema.arrow())
        buffer = io.BytesIO()
        pq.write_table(
            table,
            buffer,
            compression=COMPRESSION,
            compression_level=COMPRESSION_LEVEL,
        )
        return buffer.getvalue(), digest.hexdigest()

    # --- reading data ------------------------------------------------------

    def read(self, *, snapshot_id: int | None = None, as_of_ns: int | None = None) -> pa.Table:
        """The rows of a snapshot, optionally as of an instant.

        `snapshot_id` defaults to the current snapshot. Naming an older one
        returns exactly what that snapshot held, whatever has been appended
        since -- the storage-level form of "as seen then".
        """
        snapshot = self.current() if snapshot_id is None else self.snapshot(snapshot_id)
        if snapshot is None:
            return self.schema.arrow().empty_table()

        pieces = [pq.read_table(io.BytesIO(self.store.get(file.key))) for file in snapshot.files]
        table = pa.concat_tables(pieces) if pieces else self.schema.arrow().empty_table()
        if as_of_ns is None:
            return table

        column = self.schema.event_time_column
        if column is None:
            raise NoEventTime(
                f"{self.name} declares no event-time column, so it cannot answer a "
                "point-in-time read. Returning everything would answer a different "
                "question in a way the caller could not detect"
            )
        return table.filter(pc.less_equal(table[column], pa.scalar(as_of_ns, pa.int64())))
