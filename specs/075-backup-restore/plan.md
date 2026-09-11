# Implementation Plan: A backup is a claim about restoring

**Branch**: `wp-037-backup-restore` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

## Summary

`lakehouse/backup.py`: `back_up`, `restore` and `verify`, all three store-to-store
over the existing `ObjectStore` port.

The design is one sentence: **a backup walks snapshots oldest-first, copying each
snapshot's data files before its manifest.** Everything else — refusing a
non-empty target, reporting where a restore landed, telling a transit failure
from an identity failure — is bookkeeping around that.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: unit tests on `InMemoryObjectStore`, plus an integration test doing
the round trip on MinIO in CI. Mutation sweep over the module.

**Constraints**: no clock; `ObjectStore` gains nothing (a backup that needed a
new port operation would be reaching past what the plane guarantees).

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **V. Append-only** | A restore never rewrites; it refuses a non-empty target. | **Pass.** |
| **XI. Reproducible results** | Identity compared on the content hash, so a writer upgrade cannot make a good restore look bad. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-037`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/lakehouse/backup.py          # NEW
src/channelflow/lakehouse/__init__.py        # + exports
tests/unit/lakehouse/test_backup.py          # NEW
tests/integration/test_backup_on_minio.py    # NEW
```

**Structure Decision**: a module beside `table.py` rather than methods on
`Table`. A backup operates on a table's *keys*, not on its rows, and a `Table`
that could copy itself elsewhere would tempt a future caller into using it as a
general copy mechanism — which is how a second lineage gets merged into one
sequence.

## Why the copy walks snapshots rather than listing keys

Listing every key under the table prefix and copying it is shorter, and it
copies manifests and data in whatever order the listing returns — which is
alphabetical, which puts `metadata/` before the data directory. That is exactly
the corruption ordering.

Walking snapshots oldest-first and copying each one's named files before its
manifest also gives the interruption property for free: stop anywhere and the
copy is a prefix of the history, every manifest in it fully backed by data.

## The two failure kinds

`verify` returns a report rather than raising, because an operator needs to know
*which* problem they have:

- **missing file** — a manifest names an object that is not there; the copy is
  unusable and this is the corruption FR-001 exists to prevent;
- **byte mismatch** — the object is there and its sha256 disagrees with the
  manifest; the copy was damaged in transit and retrying may fix it;
- **identity mismatch** — the restored snapshot's content hash differs from the
  source's; a different dataset arrived, and retrying will not fix it.

Collapsing these into a boolean makes the 3am question unanswerable.
