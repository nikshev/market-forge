---
id: REQ-WP-039
title: The canonical plane migrates to Apache Iceberg
type: work-package
prd_ref: "§6.4, §7"
prd_lines: "440-450, 600-642, 786"
phase: 8
status: planned
depends_on: [REQ-STORE-001, REQ-WP-037]
tags: []
---

## Requirement

PRD §7 names the format:

    - Apache Iceberg: lakehouse table/catalog semantics for normalized, feature
      and research-grade datasets

and §6.4.4 says where it applies:

    Iceberg tables are created for normalized, feature and research-grade
    datasets where snapshot isolation, schema evolution, partition evolution and
    reproducibility matter. Raw immutable payloads may remain plain compressed
    objects/Parquet when Iceberg metadata adds no value.

[[ADR-002]] adopted "Parquet on S3-compatible object storage with Iceberg table
semantics" from the start. What exists is a hand-rolled layer implementing those
semantics, and [[ADR-060]] records why the approximation is being replaced by the
thing itself: **the layer can only append**, so nothing it offers can make a data
file unreferenced, so retention has nothing to free. Iceberg has the operation
that is missing — a delete that rewrites the live file set — and retention is
then three steps over it: delete what aged out, expire the snapshots still
pointing at the old files, remove what nothing references.

**This requirement is the migration, and its acceptance is about not losing
anything on the way.** Every property the hand-rolled plane guarantees today is a
property somebody depends on, and the migration's failure mode is not a crash —
it is arriving with a working Iceberg table that quietly stopped doing one of
them.

## Acceptance

- Point-in-time reads hold: a read at an instant returns exactly the rows
  knowable then, and appending later data does not change an earlier read.
- Snapshot isolation holds: a reader holding a snapshot is unaffected by
  concurrent commits.
- A commit is atomic: two writers racing produce one winner and one refusal, not
  a merged or partial state.
- Dataset identity is preserved: the content hash of [[ADR-053]] is still
  computed over rows, and identical data still produces an identical hash across
  processes and library versions.
- The domain tables — bars, channels, extrema, features, signals — read and
  write unchanged from their callers' point of view.
- Backup and restore ([[REQ-WP-037]]) work on the new format, with the same
  guarantees, including that an interrupted copy leaves no metadata pointing at
  absent data.
- The fast gate still runs with no services (REQ-INFRA-002).
- Expiring a snapshot frees the data files nothing references any more — the
  property whose absence forced this migration, demonstrated rather than assumed.
- Nothing in the repository still reads or writes the hand-rolled format when the
  migration is complete.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-077-iceberg]]
- **Tests:**
    - `tests/unit/lakehouse/test_iceberg.py::test_a_backfill_is_not_visible_to_an_earlier_read`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_delete_alone_frees_nothing_because_the_history_still_points_at_it`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_delete_leaves_files_nothing_references`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_point_in_time_read_without_an_event_time_is_refused`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_read_at_an_instant_excludes_later_rows`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_read_before_any_data_is_empty_rather_than_an_error`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_read_by_snapshot_returns_that_commit_s_rows`
    - `tests/unit/lakehouse/test_iceberg.py::test_a_table_nobody_has_written_to_reports_no_snapshots`
    - `tests/unit/lakehouse/test_iceberg.py::test_an_empty_append_is_refused`
    - `tests/unit/lakehouse/test_iceberg.py::test_appending_does_not_change_what_an_earlier_read_returned`
    - `tests/unit/lakehouse/test_iceberg.py::test_different_rows_hash_differently`
    - `tests/unit/lakehouse/test_iceberg.py::test_nothing_is_unreferenced_in_an_append_only_table`
    - `tests/unit/lakehouse/test_iceberg.py::test_order_within_one_commit_is_the_order_written`
    - `tests/unit/lakehouse/test_iceberg.py::test_rows_come_back_in_commit_order`
    - `tests/unit/lakehouse/test_iceberg.py::test_the_hash_does_not_depend_on_how_the_rows_were_committed`
    - `tests/unit/lakehouse/test_iceberg.py::test_the_same_rows_hash_the_same_in_two_tables`
    - `tests/unit/lakehouse/test_iceberg.py::test_the_snapshot_records_what_it_holds`
    - `tests/unit/lakehouse/test_iceberg.py::test_two_writers_from_one_parent_both_land`
- **Code:**
    - `src/channelflow/lakehouse/iceberg.py`
- **Outcomes:** [[OUT-2026-09-11-implement-iceberg]], [[OUT-2026-09-11-implement-iceberg-callers]], [[OUT-2026-09-11-plan-iceberg]], [[OUT-2026-09-11-requirement-iceberg]], [[OUT-2026-09-11-spec-iceberg]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

**Staged deliberately.** Forty-two files touch the lakehouse and twelve
construct a table. The migration lands in steps, each green, and the requirement
is not `implemented` until the last caller moves and the old format is gone —
because a half-migrated plane with two formats is the second production path
[[ADR-002]] refused.

**What Iceberg does not give us** is [[ADR-053]]'s content-addressed identity:
its snapshot ids are allocated, so two runs over identical data get different
ids. PRD §0 item 13 and [[REQ-REPRO-001]] rest on a hash of the rows, and that
stays ours to compute.
