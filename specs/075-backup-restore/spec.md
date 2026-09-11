---
traces: [REQ-WP-037]
status: draft
---

# Feature Specification: A backup is a claim about restoring

**Feature Branch**: `wp-037-backup-restore`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-037 — one of Phase 8's six remaining deliverables.

## Context

PRD §45 lists `backup/restore;` and gives it no section. The acceptance is
derived in `docs/superpowers/specs/2026-09-11-backup-restore-acceptance-design.md`.

The failure this feature exists to prevent is not losing data. It is **believing
you can get it back.** A backup nobody has restored is an untested code path
holding the data of last resort, and the moment it is exercised is the moment it
must not fail — at which point discovering that the copy was never restorable is
the worst possible time to discover it.

Two failures are specific to this system's canonical plane, and neither is
obvious from a general idea of backups.

**Copy order is correctness, not performance.** The table layer writes data
files before the manifest naming them, because an interrupted commit that leaves
orphan files is invisible to every reader, while a manifest naming files that
never arrived is corruption. A backup copying manifests first manufactures that
corruption in the copy. The restored table then reads correctly — until a query
touches the missing file.

**Landing on an earlier snapshot is both a legitimate operation and a
catastrophe**, and afterwards they are indistinguishable. The plane is
append-only and versioned, so "restore to yesterday" is a real request; "restore
landed on yesterday" is data loss wearing the shape of success.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The round trip, not the copy (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a table with several commits, **When** it is backed up and restored into an empty store, **Then** the restored table holds the same rows.
2. **Given** a restored table, **When** it is verified, **Then** every file the manifests name is present and matches its recorded byte digest.
3. **Given** a restored table, **When** its snapshot identity is compared, **Then** it equals the source's.

---

### User Story 2 - An interrupted backup is restorable (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a backup interrupted after some data files and before their manifest, **When** the partial copy is restored, **Then** it yields the last complete snapshot rather than an error.
2. **Given** the same partial copy, **When** it is verified, **Then** no manifest names an absent file.

---

### User Story 3 - Where you landed is stated (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a restore, **When** it completes, **Then** it reports the snapshot it landed on.
2. **Given** a backup whose newest snapshot is `7`, **When** a restore would land on `5` and the caller asked for nothing in particular, **Then** it is refused.
3. **Given** the same backup, **When** the caller asks for snapshot `5` by name, **Then** it restores to `5` and says so.

---

### User Story 4 - Never merged (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a target holding any object under the table's prefix, **When** a restore is attempted, **Then** it is refused.
2. **Given** the same backup restored twice into fresh targets, **When** both are read, **Then** they are identical.

### Edge Cases

- **A table with no commits.** Backing it up copies nothing and restoring yields a table with no snapshots — not an error, and not an empty first snapshot, which would be a commit that never happened.
- **A backup of a table that gained commits while copying.** The copy is consistent up to some snapshot; that snapshot is what the restore lands on and states.
- **A file present in the target but not named by any manifest.** An orphan, invisible to readers, and not a verification failure — the same rule the writer already lives by.
- **A byte digest mismatch versus a content mismatch.** Different failures reported apart: the first says the copy was damaged in transit, the second says a different dataset arrived.
- **Restoring into the store it was backed up from.** Refused by the non-empty rule, without a special case.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A backup MUST copy every data file before the manifest that names it.
- **FR-002**: A restore MUST reproduce the source table's rows.
- **FR-003**: Verification MUST confirm every manifest-named file is present.
- **FR-004**: Verification MUST compare each file's byte digest against the manifest, and report that failure distinctly from a snapshot-identity mismatch.
- **FR-005**: Verification MUST compare snapshot identity using the content hash, not the stored bytes.
- **FR-006**: A restore MUST report the snapshot it landed on.
- **FR-007**: A restore that would land short of the backup's newest snapshot MUST be refused unless that snapshot was named.
- **FR-008**: A restore into a non-empty target MUST be refused.
- **FR-009**: An interrupted backup MUST restore to its last complete snapshot.
- **FR-010**: The round trip MUST be exercised against a real object store in CI.
- **FR-011**: Nothing existing MUST change.

### Key Entities

- **Backup**: an ordered copy of a table's objects into another store.
- **Restore**: the operation that makes the claim true, and the snapshot it landed on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A three-commit table backed up and restored reads row-for-row identically.
- **SC-002**: A copy truncated before a manifest restores to the previous snapshot and verifies clean.
- **SC-003**: A copy truncated *after* a manifest and before its data would fail verification — and cannot be produced by the backup, which is what FR-001 buys.
- **SC-004**: A restore reports a snapshot id.
- **SC-005**: An unnamed restore landing short is refused; a named one succeeds.
- **SC-006**: A restore into a non-empty target is refused.
- **SC-007**: The round trip passes against MinIO in CI.

## Assumptions

- **Verification is digest-based; the tests are row-based.** An operator
  verifying a restore should not have to decode every Parquet file, so
  verification compares digests. The test suite additionally reads both tables
  and compares rows, because a digest check can only ever prove the manifests
  agree with the files — the rows are what somebody actually wanted back.
- **The backup is a store-to-store copy.** Both sides satisfy the existing
  object-store port, so a backup target can be a second bucket, a second
  endpoint or a local directory without this feature choosing.
- **Object storage only.** The canonical plane is object storage ([[ADR-002]]);
  Postgres holds operational metadata that is rebuilt rather than restored, and
  claiming otherwise would promise a guarantee nothing implements.

## Open Questions

- **Incremental backup.** The plane is append-only, so copying only new objects
  is natural — and is exactly where a subtle bug would live. Not decided here.
- **Where a backup lives**, and on what schedule. Both are deployment questions,
  and retention is Phase 8's own separate line.
