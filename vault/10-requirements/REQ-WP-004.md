---
id: REQ-WP-004
title: Order book service
type: work-package
prd_ref: "WP-004 Order book service"
prd_lines: "6959-6967"
phase: null
status: implemented
depends_on: ["REQ-WP-003"]
tags: []
---

## Requirement

- buffer + snapshot bootstrap;
- exact sequence validation;
- rebuild on gap;
- top-N access;
- depth-at-bps query;
- health state.

## Acceptance

- book bootstraps from a buffered snapshot;
- sequence numbers are validated exactly;
- book rebuilds on a detected sequence gap;
- top-N levels are accessible;
- depth-at-bps can be queried;
- book health state is reported.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-010-order-book-service]]
- **Tests:**
    - `tests/unit/book/test_bootstrap.py::test_a_buffer_that_does_not_reach_the_snapshot_fails_bootstrap`
    - `tests/unit/book/test_bootstrap.py::test_a_service_that_has_not_bootstrapped_refuses_every_read`
    - `tests/unit/book/test_bootstrap.py::test_a_snapshot_newer_than_every_buffered_delta_bootstraps_on_its_own`
    - `tests/unit/book/test_bootstrap.py::test_bootstrap_equals_applying_only_the_deltas_after_the_snapshot`
    - `tests/unit/book/test_bootstrap.py::test_deltas_arriving_after_bootstrap_apply_directly`
    - `tests/unit/book/test_health.py::test_health_is_reported_at_every_stage_of_the_lifecycle`
    - `tests/unit/book/test_health.py::test_staleness_is_not_reported_when_it_was_not_asked_for`
    - `tests/unit/book/test_health.py::test_staleness_is_the_distance_from_the_last_applied_event`
    - `tests/unit/book/test_health.py::test_staleness_is_zero_rather_than_negative_when_asked_about_the_past`
    - `tests/unit/book/test_health.py::test_the_book_package_cannot_consult_a_clock`
    - `tests/unit/book/test_health.py::test_the_same_stream_twice_gives_the_same_book_and_the_same_health`
    - `tests/unit/book/test_reads.py::test_a_short_side_returns_what_exists`
    - `tests/unit/book/test_reads.py::test_an_empty_side_has_zero_depth_when_a_mid_still_exists`
    - `tests/unit/book/test_reads.py::test_depth_is_measured_from_the_mid_and_not_from_each_side`
    - `tests/unit/book/test_reads.py::test_depth_refuses_when_one_side_is_empty`
    - `tests/unit/book/test_reads.py::test_depth_within_bps_counts_from_the_mid`
    - `tests/unit/book/test_reads.py::test_top_n_is_ordered_from_the_touch_outward`
    - `tests/unit/book/test_sequence.py::test_a_buffer_with_its_own_gap_fails_the_bootstrap`
    - `tests/unit/book/test_sequence.py::test_a_delta_that_breaks_the_sequence_changes_nothing`
    - `tests/unit/book/test_sequence.py::test_a_delta_with_no_sequence_range_is_refused`
    - `tests/unit/book/test_sequence.py::test_a_fresh_snapshot_rebuilds_the_book_and_the_gap_survives`
    - `tests/unit/book/test_sequence.py::test_a_gap_is_counted_once_and_reported`
    - `tests/unit/book/test_sequence.py::test_an_obsolete_delta_is_discarded_rather_than_counted_as_a_gap`
    - `tests/unit/book/test_sequence.py::test_every_read_refuses_after_a_gap`
    - `tests/unit/book/test_sequence.py::test_gaps_accumulate_across_rebuilds`
- **Code:**
    - `src/channelflow/book/__init__.py`
    - `src/channelflow/book/book.py`
- **Outcomes:** [[OUT-2026-09-08-implement-order-book-service]], [[OUT-2026-09-08-plan-order-book-service]], [[OUT-2026-09-08-spec-order-book-service]], [[OUT-2026-09-08-tasks-order-book-service]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
