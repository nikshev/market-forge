---
id: REQ-WP-070
title: Maintenance runs, and the deletion it runs works where the data is
type: work-package
prd_ref: "§6.4.9, §7, §45 Phase 8"
prd_lines: "735-745, 770-782, 6904-6913"
phase: 8
status: implemented
depends_on: [REQ-WP-068, REQ-WP-038, REQ-WP-065]
tags: []
---

## Requirement

[[REQ-WP-068]] left one thing open in so many words: `make compact` exists and
nothing runs it, so a deployment drifts back. Measuring what a deployment
actually holds found something worse.

### The only deletion in the system does nothing on S3

`retention.apply` is three steps, and [[ADR-062]] makes the third the only place
in this system that deletes. It asks `unreferenced_files()` what nothing points
at any more, and that walks the table's location:

    root = location.removeprefix("file://")
    if not Path(root).is_dir():
        return []

A location of `s3://channelflow-dev/warehouse/channelflow/bars` is not a
directory, so it returns nothing — **on the storage [[ADR-002]] makes the
canonical plane**. Retention then deletes nothing and reports `files_removed=0`,
which is exactly what it reports when there was nothing to delete.

Measured on the deployment: expiring 933 snapshots freed **zero bytes**. The
table holds 933 parquet files of which its current snapshot uses one, 7,480
metadata files, and 315 MB for a few hundred kilobytes of bars.

Retention is tested only in `tests/unit/lakehouse/`, against a local warehouse,
where the walk works. Nothing exercised it where it is used.

### And nothing runs maintenance anyway

Compaction fixes read time and frees nothing; retention frees bytes and does not
compact. Both are needed, on a schedule, or a deployment degrades in two
directions at once — the read cost [[REQ-WP-067]] caught, and storage that only
grows.

## Acceptance

- `unreferenced_files()` enumerates objects when the location is an object store,
  and **refuses rather than returning nothing** for a location it cannot walk. A
  deletion pass that cannot list is a pass that must not report success.
- An integration test against MinIO proves a file is actually removed — the
  gap that let this survive was that nothing tested the deletion where it runs.
- A maintenance pass composes compaction and retention, in that order, and
  reports what each did.
- It runs on a schedule, as a service of the deployment, with the interval and
  the retention policy configured rather than compiled in.
- The pass is skippable per table and refuses an unknown one, so an operator
  can run it against one table without learning the list by trial.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-111-maintenance]]
- **Tests:**
    - `tests/integration/test_lakehouse_on_minio.py::test_a_location_that_cannot_be_listed_is_refused`
    - `tests/integration/test_lakehouse_on_minio.py::test_a_maintenance_pass_frees_objects_and_keeps_the_rows`
    - `tests/integration/test_lakehouse_on_minio.py::test_unreferenced_files_are_found_on_an_object_store`
    - `tests/unit/lakehouse/test_maintenance.py::test_a_new_table_is_created_already_pruning`
    - `tests/unit/lakehouse/test_maintenance.py::test_a_pass_compacts_and_reports_what_it_found`
    - `tests/unit/lakehouse/test_maintenance.py::test_a_pass_without_a_policy_expires_nothing`
    - `tests/unit/lakehouse/test_maintenance.py::test_a_table_that_predates_the_property_gets_it`
    - `tests/unit/lakehouse/test_maintenance.py::test_compaction_happens_before_retention`
    - `tests/unit/lakehouse/test_maintenance.py::test_the_line_says_what_happened`
- **Code:**
    - `src/channelflow/lakehouse/maintenance.py`
- **Outcomes:** [[OUT-2026-09-14-implement-maintenance]]
<!-- trace:end -->

## Notes

The order matters. Compaction unreferences the old files; retention expires the
snapshots that still name them and then removes them. Reversed, retention finds
nothing unreferenced and compaction's output waits a full cycle to be collected.
