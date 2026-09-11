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
- A restore is verified by `content_sha256` — the logical dataset — not by byte
  equality, which [[ADR-053]] already showed changes when a writer library is
  upgraded and nothing about the data has.
- Byte equality is asserted where it is genuinely expected, and a mismatch there
  means something different from a content mismatch; the two failures are
  reported apart.
- Data files are copied before the manifests that name them, and a backup
  interrupted partway leaves a restorable earlier state rather than a manifest
  naming absent files.
- A restore states which snapshot it landed on.
- Landing short of the newest snapshot in the backup is refused unless the
  caller asked for that snapshot by name.
- Restoring into a non-empty target is refused rather than merged.
- The round trip is verified against a real object store in CI, with the
  in-memory store carrying the logic tests ([[ADR-002]], CLAUDE.md's two gates).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-075-backup-restore]]
- **Tests:**
    - `tests/integration/test_backup_on_minio.py::test_a_table_survives_a_round_trip_through_a_real_object_store`
    - `tests/integration/test_backup_on_minio.py::test_re_running_a_backup_copies_nothing_and_raises_nothing`
    - `tests/integration/test_backup_on_minio.py::test_restoring_over_a_live_table_is_refused_on_the_real_backend`
    - `tests/integration/test_backup_on_minio.py::test_the_copy_verifies_against_the_source_s_identity`
    - `tests/unit/lakehouse/test_backup.py::test_a_backed_up_table_restores_row_for_row`
    - `tests/unit/lakehouse/test_backup.py::test_a_clean_copy_verifies`
    - `tests/unit/lakehouse/test_backup.py::test_a_different_dataset_is_an_identity_failure`
    - `tests/unit/lakehouse/test_backup.py::test_a_hole_deep_in_the_history_is_found_too`
    - `tests/unit/lakehouse/test_backup.py::test_a_hole_in_the_history_is_found_even_when_the_latest_commit_is_whole`
    - `tests/unit/lakehouse/test_backup.py::test_a_key_already_holding_something_else_is_refused_not_overwritten`
    - `tests/unit/lakehouse/test_backup.py::test_a_missing_file_is_reported_as_missing`
    - `tests/unit/lakehouse/test_backup.py::test_a_restore_says_which_snapshot_it_landed_on`
    - `tests/unit/lakehouse/test_backup.py::test_a_schema_free_table_backs_up_too`
    - `tests/unit/lakehouse/test_backup.py::test_a_table_nobody_ever_committed_to_restores_as_one`
    - `tests/unit/lakehouse/test_backup.py::test_an_interrupted_backup_never_leaves_a_manifest_over_absent_data`
    - `tests/unit/lakehouse/test_backup.py::test_an_interrupted_backup_restores_to_its_last_complete_snapshot`
    - `tests/unit/lakehouse/test_backup.py::test_an_orphan_object_is_not_a_failure`
    - `tests/unit/lakehouse/test_backup.py::test_asking_for_a_snapshot_the_backup_does_not_hold_is_refused`
    - `tests/unit/lakehouse/test_backup.py::test_copying_an_object_that_is_already_there_writes_nothing`
    - `tests/unit/lakehouse/test_backup.py::test_damage_in_transit_is_reported_as_corrupt_not_missing`
    - `tests/unit/lakehouse/test_backup.py::test_landing_short_is_allowed_when_it_was_asked_for`
    - `tests/unit/lakehouse/test_backup.py::test_landing_short_without_being_asked_is_refused`
    - `tests/unit/lakehouse/test_backup.py::test_one_absent_file_is_one_finding_however_many_manifests_name_it`
    - `tests/unit/lakehouse/test_backup.py::test_re_running_an_interrupted_backup_completes_it`
    - `tests/unit/lakehouse/test_backup.py::test_restoring_into_a_non_empty_target_is_refused`
    - `tests/unit/lakehouse/test_backup.py::test_the_restored_table_keeps_the_same_snapshot_identity`
    - `tests/unit/lakehouse/test_backup.py::test_two_restores_into_fresh_targets_agree`
- **Code:**
    - `src/channelflow/lakehouse/backup.py`
- **Outcomes:** [[OUT-2026-09-11-implement-backup-restore]], [[OUT-2026-09-11-plan-backup-restore]], [[OUT-2026-09-11-requirement-backup-restore]], [[OUT-2026-09-11-spec-backup-restore]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Deliberately out of scope, and argued in the derivation document: retention and
scheduling (§6.4.9 and Phase 8's own "S3 cold retention" line), Postgres
metadata (rebuilt, not restored), and encryption (§34 says nothing about it, and
inventing a criterion would be writing requirements rather than deriving them).
