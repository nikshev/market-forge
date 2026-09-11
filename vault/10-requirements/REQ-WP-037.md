---
id: REQ-WP-037
title: A backup is a claim about restoring, so the test restores
type: work-package
prd_ref: "§45 Phase 8"
prd_lines: "6912"
phase: 8
status: implemented
depends_on: [REQ-STORE-001]
tags: []
---

## Requirement

PRD §45's Phase 8 lists:

    - backup/restore;

and gives it no section of its own. The acceptance below is therefore
**derived, not quoted**; each line names the PRD text behind it in
`docs/superpowers/specs/2026-09-11-backup-restore-acceptance-design.md`.

Two sentences elsewhere in the PRD say what a backup is for. §0 item 13 asks a
result to be reproducible from "a versioned dataset + config + code commit hash
+ model artifact hash", and §6.4.3 requires retention "long enough for
operational replay/recovery". Both describe recovery as something a person
performs, not as bytes that exist somewhere.

**A backup nobody has restored is an untested code path holding the data of last
resort**, and the moment it is exercised is the moment it must not fail.

Two more things follow from the canonical plane's own shape rather than from a
general idea of backups.

**The copy inherits the writer's ordering.** `lakehouse/table.py` writes data
files before the manifest naming them, and says why: a commit that dies halfway
leaves orphan files, which no reader can see, whereas a manifest naming files
that never arrived is corruption. A backup copying in any other order
manufactures that corruption in the copy, and the restored table reads correctly
until something touches the missing file.

**Landing on an earlier snapshot is a legitimate operation and a catastrophic
accident**, and afterwards the two are indistinguishable. The requirement is not
that a restore always lands on the newest snapshot; it is that it says which one
it landed on, and that landing short of the newest was asked for.

## Acceptance

- A backup can be restored, and the test performs the round trip rather than
  asserting that a copy exists.
- **Narrowed by [[ADR-061]]**: a restore lands at the location the backup was
  taken from. Iceberg's metadata holds absolute URIs, so a tree restored
  elsewhere names a place that holds nothing. Losing a bucket's contents is
  still recoverable; restoring under a *different* name is not, and that is a
  reduction from what this requirement first delivered.
- A restore is verified against the dataset, not against bytes, for the reason
  [[ADR-053]] gives: a writer upgrade changes the bytes and not the data. On the
  Iceberg layout this is the rows a restored table reads back.
- Data files are copied before the manifests that name them, those before the
  manifest list, and that before the metadata naming it — so a backup
  interrupted partway leaves a restorable earlier state rather than metadata
  over absent data.
- The copy reads and writes through the same client the table commits through,
  so a backup of the storage the system actually uses is possible. A backup that
  only worked against a local warehouse would not be a backup.
- A restore states which snapshot it landed on.
- Restoring into a catalog that already holds the table is refused rather than
  merged.
- The round trip is verified against a real object store in CI, with the
  in-memory store carrying the logic tests ([[ADR-002]], CLAUDE.md's two gates).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-075-backup-restore]]
- **Tests:**
    - `tests/integration/test_backup_on_minio.py::test_a_table_in_the_bucket_backs_up_and_restores`
    - `tests/integration/test_backup_on_minio.py::test_a_table_on_the_real_store_verifies_whole`
    - `tests/unit/lakehouse/test_backup.py::test_a_backed_up_table_restores_row_for_row`
    - `tests/unit/lakehouse/test_backup.py::test_a_missing_file_is_found_wherever_in_the_history_it_is`
    - `tests/unit/lakehouse/test_backup.py::test_a_restore_says_where_it_landed`
    - `tests/unit/lakehouse/test_backup.py::test_a_table_nobody_committed_to_backs_up_as_nothing`
    - `tests/unit/lakehouse/test_backup.py::test_a_table_with_nothing_in_it_verifies`
    - `tests/unit/lakehouse/test_backup.py::test_a_whole_table_verifies`
    - `tests/unit/lakehouse/test_backup.py::test_an_interrupted_backup_never_leaves_metadata_over_absent_data`
    - `tests/unit/lakehouse/test_backup.py::test_point_in_time_reads_survive_the_round_trip`
    - `tests/unit/lakehouse/test_backup.py::test_re_running_a_backup_copies_nothing_and_raises_nothing`
    - `tests/unit/lakehouse/test_backup.py::test_restoring_from_somewhere_holding_no_backup_is_refused`
    - `tests/unit/lakehouse/test_backup.py::test_restoring_over_an_existing_table_is_refused`
- **Code:**
    - `src/channelflow/lakehouse/backup.py`
- **Outcomes:** [[OUT-2026-09-11-implement-backup-restore]], [[OUT-2026-09-11-implement-iceberg-complete]], [[OUT-2026-09-11-plan-backup-restore]], [[OUT-2026-09-11-requirement-backup-restore]], [[OUT-2026-09-11-spec-backup-restore]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Deliberately out of scope, and argued in the derivation document: retention and
scheduling (§6.4.9 and Phase 8's own "S3 cold retention" line), Postgres
metadata (rebuilt, not restored), and encryption (§34 says nothing about it, and
inventing a criterion would be writing requirements rather than deriving them).
