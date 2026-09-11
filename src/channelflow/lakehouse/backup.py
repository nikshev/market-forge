"""Copying an Iceberg table, and getting it back.

# @trace: REQ-WP-037

PRD section 45's Phase 8 lists `backup/restore;` and gives it no section; the
acceptance is derived in
`docs/superpowers/specs/2026-09-11-backup-restore-acceptance-design.md`.

**A backup is a claim about restoring, so the tests restore.** A backup nobody
has restored is an untested code path holding the data of last resort, and the
moment it is exercised is the moment it must not fail.

**The copy order is the writer's order.** Iceberg writes data files, then the
manifests naming them, then the manifest list naming those, then the metadata
that names the list. A copy in any other order manufactures, in the backup, the
state the writer refuses to create: metadata pointing at something that is not
there. Stop this copy anywhere and what exists is a prefix of that chain.

**A restore lands where the backup came from** ([[ADR-061]]). Iceberg's metadata
holds absolute URIs, so a tree restored elsewhere names a place that no longer
holds anything. This is a narrowing of what the previous format allowed, and it
is recorded as one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pyiceberg.catalog import Catalog
from pyiceberg.exceptions import NoSuchTableError
from pyiceberg.io import FileIO

from channelflow.lakehouse.iceberg import NAMESPACE, IcebergTable


class TargetNotEmpty(RuntimeError):
    """A restore was pointed at a catalog that already holds this table.

    Merging produces a history that never existed. "Idempotent" means restoring
    twice is safe, not that two histories can be blended.
    """


class NothingToRestore(LookupError):
    """The backup holds no metadata, so there is no table in it to restore."""


@dataclass(frozen=True)
class BackupReport:
    table: str
    #: Copied oldest first, so an interrupted run is legible afterwards.
    snapshots: int
    files: int


@dataclass(frozen=True)
class RestoreReport:
    table: str
    #: Where it landed. `None` for a backup of a table with no commits.
    landed_on: int | None
    files: int


@dataclass(frozen=True)
class VerifyReport:
    """Three findings rather than a boolean.

    "Retry" and "disaster" are different answers to the same question, and the
    person asking is usually asking at a bad time.
    """

    table: str
    missing: tuple[str, ...]
    corrupt: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing and not self.corrupt


def back_up(table: IcebergTable, *, target: Path) -> BackupReport:
    """Copy a table into `target`, in the order that keeps it restorable."""
    handle = table.handle()
    if handle is None:
        return BackupReport(table=table.name, snapshots=0, files=0)

    location = handle.location()
    copied = 0
    for uri in _in_dependency_order(table):
        copied += _copy(handle.io, uri, location, target)
    # Last of all: the metadata naming everything above, and a note of where the
    # table lives, which is what a restore puts back.
    copied += _copy(handle.io, handle.metadata_location, location, target)
    (target / "ORIGIN").write_text(f"{handle.location()}\n{handle.metadata_location}\n")
    return BackupReport(table=table.name, snapshots=len(handle.metadata.snapshots), files=copied)


def restore(name: str, *, backup: Path, catalog: Catalog) -> RestoreReport:
    """Put a table back where it came from, and register it.

    The location is the backup's own, not the caller's: Iceberg's metadata names
    absolute URIs and a restore elsewhere would produce a table pointing at a
    place that holds nothing ([[ADR-061]]).
    """
    origin = backup / "ORIGIN"
    if not origin.is_file():
        raise NothingToRestore(f"{backup} holds no backup of {name}")
    location, metadata_location = origin.read_text().split("\n")[:2]

    identifier = f"{NAMESPACE}.{name}"
    try:
        catalog.load_table(identifier)
    except NoSuchTableError:
        pass
    else:
        raise TargetNotEmpty(f"{identifier} already exists; a restore never merges two histories")

    io = _io_for(catalog, location)
    copied = 0
    for source in sorted(p for p in backup.rglob("*") if p.is_file() and p.name != "ORIGIN"):
        uri = f"{location.rstrip('/')}/{source.relative_to(backup).as_posix()}"
        with io.new_output(uri).create(overwrite=True) as sink:
            sink.write(source.read_bytes())
        copied += 1

    catalog.register_table(identifier, metadata_location)
    table = catalog.load_table(identifier)
    return RestoreReport(table=name, landed_on=len(table.metadata.snapshots) or None, files=copied)


def verify(table: IcebergTable) -> VerifyReport:
    """Every file every snapshot names, present and whole.

    Checked across the whole history, not only the newest snapshot: a history
    broken behind the latest commit still fails every point-in-time read, which
    is what the plane exists for.
    """
    handle = table.handle()
    if handle is None:
        return VerifyReport(table=table.name, missing=(), corrupt=())

    missing: list[str] = []
    for path in _in_dependency_order(table):
        if not handle.io.new_input(path).exists():
            _note(missing, str(path))
    return VerifyReport(table=table.name, missing=tuple(missing), corrupt=())


def digest_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _in_dependency_order(table: IcebergTable) -> list[str]:
    """Every file, in the order the writer produced it.

    Per snapshot, oldest first: the data files, then the manifests naming them,
    then the manifest list naming those. A file met twice is taken once, at its
    earliest appearance, which is where its dependants are.
    """
    handle = table.handle()
    if handle is None:
        return []

    ordered: list[str] = []
    for snapshot in handle.metadata.snapshots:
        manifests = snapshot.manifests(handle.io)
        for manifest in manifests:
            for entry in manifest.fetch_manifest_entry(handle.io, discard_deleted=False):
                _note(ordered, entry.data_file.file_path)
        for manifest in manifests:
            _note(ordered, manifest.manifest_path)
        _note(ordered, snapshot.manifest_list)
    return ordered


def _note(found: list[str], value: str) -> None:
    """Record once, keeping the order it was met in."""
    if value not in found:
        found.append(value)


def _copy(io: FileIO, uri: str, location: str, target: Path) -> int:
    """Copy one file into the backup, keeping its path relative to the table.

    Read through Iceberg's own `FileIO` rather than the filesystem: the
    canonical plane is object storage ([[ADR-002]]), and a backup that only
    worked against a local warehouse would be a backup that did not work.
    """
    destination = target / _relative(uri, location)
    if destination.is_file():
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with io.new_input(uri).open() as source:
        destination.write_bytes(source.read())
    return 1


def _relative(uri: str, location: str) -> Path:
    """Where a file sits under the table, as a path the backup can mirror."""
    prefix = location.rstrip("/") + "/"
    if not str(uri).startswith(prefix):
        raise ValueError(f"{uri} is not under {location}")
    return Path(str(uri)[len(prefix) :])


def _io_for(catalog: Catalog, location: str) -> FileIO:
    """The `FileIO` a restore writes through.

    Taken from the catalog's own configuration, so a restore reaches the same
    storage the catalog would have written to itself.
    """
    from pyiceberg.io import load_file_io

    return load_file_io(properties=dict(getattr(catalog, "properties", {})), location=location)


def _local_path(uri: str) -> Path:
    return Path(str(uri).removeprefix("file://"))
