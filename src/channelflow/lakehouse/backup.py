"""Copying the canonical plane, and getting it back.

# @trace: REQ-WP-037

PRD section 45's Phase 8 lists `backup/restore;` and gives it no section; the
acceptance is derived in
`docs/superpowers/specs/2026-09-11-backup-restore-acceptance-design.md`.

**The copy walks snapshots; it does not list keys.** `table.py` writes data
files before the manifest naming them, and says why: a commit that dies halfway
leaves orphan data files, which no reader can see, whereas a manifest naming
files that never arrived is corruption. A backup that copies in the other order
manufactures that corruption in the copy, and the restored table reads correctly
until a query touches the missing file.

The shorter implementation -- list every key under the table prefix and copy it
-- is **not** unsafe here, and an earlier version of this docstring claimed it
was. `data/` sorts before `metadata/`, so a sorted listing happens to copy data
first and satisfies the ordering by coincidence of two directory names. The walk
satisfies it by construction: it reads each manifest and copies the files that
manifest names before the manifest itself. Rename either directory and the
listing silently begins manufacturing the corruption; the walk cannot, because
it never depended on the names.

Walking oldest-first also gives the interruption property for nothing: stop
anywhere and the copy is a prefix of the history in which every manifest is
fully backed by its data.

Nothing here needs a `Schema`. A backup operates on a table's keys, not on its
rows, which is also why it is a module rather than a method on `Table`: a table
that can copy itself elsewhere invites use as a general copy mechanism, and that
is how two lineages end up merged under one version sequence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from channelflow.lakehouse.snapshot import Snapshot
from channelflow.lakehouse.store import KeyExists, ObjectStore
from channelflow.lakehouse.table import VERSION_DIGITS, NoSuchSnapshot


class TargetNotEmpty(RuntimeError):
    """A restore was pointed at a table that already holds something.

    Merging produces a version history that never existed -- manifests from two
    lineages under one sequence. "Idempotent" means restoring twice is safe, not
    that two histories can be blended.
    """


class WouldLandShort(RuntimeError):
    """The newest snapshot in the copy is not restorable, and none was named.

    Restoring to an earlier point is a legitimate request; arriving there by
    accident is indistinguishable from it afterwards. So the caller who wants an
    older snapshot names it, and the caller who names nothing gets the newest or
    an error -- never a quiet older one.
    """


class BackupConflict(RuntimeError):
    """The target already holds this key with different content.

    Not overwritten: two backups of different tables under one name, or a
    half-copied object from a different source, are both bugs that overwriting
    would hide.
    """


@dataclass(frozen=True)
class BackupReport:
    table: str
    #: Copied, oldest first, so an interrupted run is legible afterwards.
    snapshots: tuple[int, ...]
    objects: int


@dataclass(frozen=True)
class RestoreReport:
    table: str
    #: Where it landed. `None` is a table that never had a commit -- a different
    #: fact from an empty first snapshot, which would be a commit that never
    #: happened.
    landed_on: int | None
    newest_available: int | None
    objects: int


@dataclass(frozen=True)
class VerifyReport:
    """Three findings rather than a boolean.

    "Retry" and "disaster" are different answers to the same question, and the
    person asking it is usually asking at a bad time:

    - `missing` -- a manifest names an object that is not there. This is the
      corruption the copy order exists to prevent, and the copy is unusable.
    - `corrupt` -- the object is there and its bytes disagree with the manifest.
      Damage in transit; retrying may fix it.
    - `identity_ok` -- the newest snapshot's content hash matches what was
      expected. False means a different dataset arrived, and retrying will not
      fix that.
    """

    table: str
    missing: tuple[str, ...]
    corrupt: tuple[str, ...]
    identity_ok: bool

    @property
    def ok(self) -> bool:
        return not self.missing and not self.corrupt and self.identity_ok


def back_up(name: str, *, source: ObjectStore, target: ObjectStore) -> BackupReport:
    """Copy a table, in the order that keeps an interrupted copy restorable."""
    copied = 0
    done: list[int] = []
    for version, manifest_key in _manifests(source, name):
        snapshot = Snapshot.deserialize(source.get(manifest_key))
        for data_file in snapshot.files:
            copied += _copy(source, target, data_file.key)
        # Last, always. Everything it names is already here.
        copied += _copy(source, target, manifest_key)
        done.append(version)
    return BackupReport(table=name, snapshots=tuple(done), objects=copied)


def restore(
    name: str,
    *,
    source: ObjectStore,
    target: ObjectStore,
    snapshot_id: int | None = None,
) -> RestoreReport:
    """Copy a table back, and say where it landed."""
    if target.list(f"{name}/"):
        raise TargetNotEmpty(
            f"{name} already holds objects in the target; a restore never merges two histories"
        )

    manifests = _manifests(source, name)
    if not manifests:
        return RestoreReport(table=name, landed_on=None, newest_available=None, objects=0)

    available = [version for version, _ in manifests]
    if snapshot_id is not None and snapshot_id not in available:
        raise NoSuchSnapshot(f"the backup of {name} holds {tuple(available)}, not {snapshot_id}")

    complete = _newest_complete(source, manifests)
    newest = available[-1]
    if snapshot_id is None and complete != newest:
        raise WouldLandShort(
            f"the newest snapshot of {name} in this copy is {newest}, but only {complete} "
            "can be restored; name the snapshot you want if that is what you meant"
        )

    wanted = snapshot_id if snapshot_id is not None else complete
    copied = 0
    for version, manifest_key in manifests:
        if version > (wanted or 0):
            break
        snapshot = Snapshot.deserialize(source.get(manifest_key))
        for data_file in snapshot.files:
            copied += _copy(source, target, data_file.key)
        copied += _copy(source, target, manifest_key)

    return RestoreReport(table=name, landed_on=wanted, newest_available=newest, objects=copied)


def verify(
    name: str,
    *,
    store: ObjectStore,
    expect_content_hash: str | None = None,
) -> VerifyReport:
    """Check every snapshot, not only the newest.

    A manifest is cumulative -- snapshot N names every file up to N -- so the
    newest manifest alone already covers every data file. What it does *not*
    cover is the history behind it: a missing intermediate manifest leaves the
    latest read working and every point-in-time read before it broken, which is
    what the plane exists for. So each snapshot's parent is checked too.

    Each finding is reported once. A file named by four manifests and absent
    once is one problem, and listing it four times buries the other three.

    An object present but named by no manifest is **not** a finding. The writer
    already tolerates orphans -- a reader only ever opens files a manifest lists
    -- and a backup inventing a stricter rule would report corruption where the
    system deliberately accepts waste.
    """
    missing: list[str] = []
    corrupt: list[str] = []
    newest: Snapshot | None = None
    manifests = _manifests(store, name)
    present_manifests = {version for version, _ in manifests}

    for _, manifest_key in manifests:
        snapshot = Snapshot.deserialize(store.get(manifest_key))
        newest = snapshot
        if snapshot.parent_id is not None and snapshot.parent_id not in present_manifests:
            _note(missing, _manifest_key(name, snapshot.parent_id))
        for data_file in snapshot.files:
            try:
                body = store.get(data_file.key)
            except LookupError:
                _note(missing, data_file.key)
                continue
            # A copy re-encodes nothing, so byte equality is genuinely expected
            # here -- [[ADR-053]]'s warning is about comparing re-encoded data,
            # and a mismatch on a copy is genuinely damage.
            if hashlib.sha256(body).hexdigest() != data_file.file_sha256:
                _note(corrupt, data_file.key)

    identity_ok = True
    if expect_content_hash is not None:
        identity_ok = newest is not None and newest.content_hash == expect_content_hash

    return VerifyReport(
        table=name,
        missing=tuple(missing),
        corrupt=tuple(corrupt),
        identity_ok=identity_ok,
    )


def _note(found: list[str], key: str) -> None:
    """Record a finding once, keeping the order it was met in."""
    if key not in found:
        found.append(key)


def _manifest_key(name: str, version: int) -> str:
    return f"{name}/metadata/v{version:0{VERSION_DIGITS}d}.json"


def _manifests(store: ObjectStore, name: str) -> list[tuple[int, str]]:
    """Every manifest, oldest first. No `Schema` needed, and none consulted."""
    prefix = f"{name}/metadata/"
    found: list[tuple[int, str]] = []
    for key in store.list(prefix):
        stem = key[len(prefix) :]
        if not stem.startswith("v") or not stem.endswith(".json"):
            continue
        if len(stem) != VERSION_DIGITS + len("v.json"):
            continue
        found.append((int(stem[1:-5]), key))
    return sorted(found)


def _newest_complete(store: ObjectStore, manifests: list[tuple[int, str]]) -> int:
    """The newest snapshot whose files are all present.

    A backup this module produced can never differ from the newest manifest --
    that is what the ordering buys. A damaged copy can, and the difference is
    what tells a restore it is about to land short.
    """
    complete = 0
    for version, manifest_key in manifests:
        snapshot = Snapshot.deserialize(store.get(manifest_key))
        if any(not _present(store, f.key) for f in snapshot.files):
            break
        complete = version
    return complete


def _present(store: ObjectStore, key: str) -> bool:
    try:
        store.get(key)
    except LookupError:
        return False
    return True


def _copy(source: ObjectStore, target: ObjectStore, key: str) -> int:
    """Copy one object, or leave an identical one alone.

    `put_if_absent` rather than `put`, which makes re-running an interrupted
    backup safe by construction and turns a content disagreement into an error
    instead of an overwrite.
    """
    body = source.get(key)
    try:
        target.put_if_absent(key, body)
    except KeyExists:
        if target.get(key) != body:
            raise BackupConflict(key) from None
        return 0
    return 1
