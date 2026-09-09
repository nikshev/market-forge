"""A snapshot: what a table held at one commit, and how to name it.

# @trace: REQ-STORE-001

PRD section 29.B: "Every research-grade table must support dataset
lineage/snapshot reproducibility." PRD section 0 item 13 asks for a result to be
reproducible from "a versioned dataset + config + code commit hash + model
artifact hash". `Snapshot.content_hash` is the first of those four.

**The content hash is over the logical content, never over the Parquet bytes.**
That is the load-bearing decision here ([[ADR-053]]) and it is not obvious, so:
Parquet's footer carries a `created_by` string naming the writer version. On the
machine this was written, `parquet-cpp-arrow version 25.0.1` sits in every file,
which means an identical dataset written after a library upgrade produces
different bytes and a different digest. A dataset identity that changed when
nobody changed the data would make the reproducibility claim in section 0 item
13 worthless -- a research run would stop matching its own dataset for a reason
having nothing to do with the data.

So each file carries two digests, and they answer different questions.
`content_sha256` is over the rows and is what identity is built from;
`file_sha256` is over the stored bytes and answers whether *this file* is the
one that was written.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


class ManifestTampered(ValueError):
    """A manifest disagrees with itself, or with the files it lists."""


def _as_int(raw: dict[str, object], field: str) -> int:
    """One integer out of a parsed manifest, or a refusal.

    A manifest is JSON that something else wrote. Coercing whatever is there
    would turn `"12"` and `12.9` into plausible record counts, and a record
    count that disagrees with its file is how a truncated read looks like a
    short table.
    """
    value = raw[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestTampered(f"manifest field {field!r} is {value!r}; it has to be an integer")
    return value


@dataclass(frozen=True)
class DataFile:
    """One Parquet file, and the two things worth knowing about it."""

    key: str
    record_count: int
    byte_size: int
    #: Over the stored bytes. Integrity of this file, and nothing else: it
    #: changes when the writer version changes, even though the data has not.
    file_sha256: str
    #: Over the rows, in the schema's own encoding. Writer-independent, and what
    #: a snapshot's identity is built from.
    content_sha256: str

    def as_json(self) -> dict[str, object]:
        return {
            "key": self.key,
            "record_count": self.record_count,
            "byte_size": self.byte_size,
            "file_sha256": self.file_sha256,
            "content_sha256": self.content_sha256,
        }

    @staticmethod
    def from_json(raw: dict[str, object]) -> DataFile:
        return DataFile(
            key=str(raw["key"]),
            record_count=_as_int(raw, "record_count"),
            byte_size=_as_int(raw, "byte_size"),
            file_sha256=str(raw["file_sha256"]),
            content_sha256=str(raw["content_sha256"]),
        )


@dataclass(frozen=True)
class Snapshot:
    """One commit of a table: its files, its schema, and its parent.

    Immutable in the strong sense: a snapshot's manifest is written once, under a
    key that names its own version, and nothing ever rewrites it. Appending data
    writes a *new* manifest at the next version. That is PRD section 0 item 5's
    "do not rewrite historical snapshots" applied one level below the domain --
    the rule is the same rule, and here it is a property of the key space rather
    than a discipline.
    """

    snapshot_id: int
    parent_id: int | None
    schema_fingerprint: str
    files: tuple[DataFile, ...]
    #: The latest event time among the rows this commit added -- not a commit
    #: time. Nothing here reads a clock, so there is no commit time to record,
    #: and calling this one would be a wall-clock reading by another name. It can
    #: move backwards when a later append carries older rows; `snapshot_id` is
    #: what orders the chain. A table with no event-time column reports 0.
    event_time_max_ns: int

    @property
    def record_count(self) -> int:
        return sum(file.record_count for file in self.files)

    @property
    def content_hash(self) -> str:
        """This snapshot's dataset identity.

        Over the schema fingerprint and its files' *content* digests, sorted --
        so it does not depend on the order the files were listed in, and adding
        a file to a later snapshot does not require rehashing the earlier ones.

        An empty snapshot hashes its schema alone, which is a real identity: a
        table that exists and holds nothing is not the same as a table that
        holds one row, and neither is the same as a table with other columns.
        """
        digest = hashlib.sha256()
        digest.update(self.schema_fingerprint.encode())
        for content in sorted(file.content_sha256 for file in self.files):
            digest.update(content.encode())
        return digest.hexdigest()

    def as_json(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "parent_id": self.parent_id,
            "schema_fingerprint": self.schema_fingerprint,
            "event_time_max_ns": self.event_time_max_ns,
            "files": [file.as_json() for file in self.files],
            # Written into the manifest as well as computed, so a reader can
            # tell that the manifest it holds is the one that was committed --
            # a recomputed hash that disagrees means the manifest was edited.
            "content_hash": self.content_hash,
        }

    def serialize(self) -> bytes:
        """The manifest's bytes.

        `sort_keys` and a fixed separator: a manifest is written once and read
        by anything, and a JSON encoder's default spacing is not a stable
        contract.
        """
        return json.dumps(self.as_json(), sort_keys=True, separators=(",", ":")).encode()

    @staticmethod
    def deserialize(raw: bytes) -> Snapshot:
        parsed = json.loads(raw.decode())
        if not isinstance(parsed, dict):
            raise ManifestTampered("a manifest is a JSON object; this one is not")
        snapshot = Snapshot(
            snapshot_id=_as_int(parsed, "snapshot_id"),
            parent_id=(None if parsed["parent_id"] is None else _as_int(parsed, "parent_id")),
            schema_fingerprint=str(parsed["schema_fingerprint"]),
            files=tuple(DataFile.from_json(file) for file in parsed["files"]),
            event_time_max_ns=_as_int(parsed, "event_time_max_ns"),
        )
        recorded = str(parsed.get("content_hash", ""))
        if recorded and recorded != snapshot.content_hash:
            raise ManifestTampered(
                f"snapshot {snapshot.snapshot_id}'s manifest records content hash "
                f"{recorded} and its files hash to {snapshot.content_hash}; the "
                "manifest was changed after it was committed"
            )
        return snapshot
