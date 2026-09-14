---
traces: [REQ-WP-070]
status: draft
---

# Feature Specification: Maintenance, and a deletion that works

**Feature Branch**: `wp-070-maintenance`

**Created**: 2026-09-14

**Status**: Draft

**Input**: REQ-WP-070 — the scheduled pass REQ-WP-068 left open.

## Context

`unreferenced_files()` walked a table's location with `Path.is_dir()`, false for
`s3://`, so on the canonical plane it returned nothing and retention reported
`files_removed=0` — the same thing it reports when there is nothing to remove.
Retention was tested only against a local warehouse.

Measured on a deployment: 2.6 MB of data against 304.9 MB of metadata, and 933
data files where the current snapshot used one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The deletion deletes (Priority: P1)

**Acceptance**: against MinIO, files a live snapshot no longer names are found
and removed; a location that cannot be listed raises.

### User Story 2 - One pass does all three (Priority: P1)

**Acceptance**: prune metadata, compact, then expire — in that order, each
reported.

### User Story 3 - It runs without being asked (Priority: P1)

**Acceptance**: a compose service loops at a configured interval.

### User Story 4 - Forgetting is a decision (Priority: P1)

**Acceptance**: with no policy nothing is expired; the pass still compacts.

### Edge Cases

- Compaction alone orphans nothing: history still names the old files.
- A table created after this never accumulates metadata; one created before
  needs the property set.
- One table failing must not end the pass.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `_walk` lists object stores through the table's own FileIO.
- **FR-002**: A location it cannot enumerate raises `CannotList`.
- **FR-003**: New tables are created with metadata pruning on.
- **FR-004**: `prune_metadata()` sets it on existing tables, idempotently.
- **FR-005**: `maintenance.run` orders prune, compact, retain.
- **FR-006**: Retention is optional and off by default.
- **FR-007**: A `maintenance` service loops at a configured interval.
- **FR-008**: A failing table is reported and the pass continues.

### Key Entities

- **MaintenanceReport**, **CannotList**, **METADATA_PRUNING**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the deployment, 721 orphans found where zero were before.
- **SC-002**: A pass removed 218 files and kept every row.
- **SC-003**: Sixty commits: 61 metadata files and 2020 KiB without pruning, 6
  and 710 KiB with.
- **SC-004**: Mutating the order, the policy check or the pruning is caught.

## Assumptions

- Historical metadata written before pruning sheds over subsequent commits, as
  Iceberg keeps the last twenty.

## Open Questions

- `unreferenced_files` collects data files by contract; orphaned manifests are
  Iceberg's own to prune and are not swept here.
