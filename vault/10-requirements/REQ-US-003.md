---
id: REQ-US-003
title: Verify non-repainting
type: user-story
prd_ref: "US-003 — Verify non-repainting"
prd_lines: "259-262"
phase: null
status: implemented
depends_on: ["REQ-API-001", "REQ-WP-006"]
tags: []
---

## Requirement

As a researcher, I want to compare the historical snapshot of the channel that actually existed at that moment against the model's later state.

## Acceptance

- the historical channel snapshot as it existed at the time is available for comparison against the model's current/later state.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-028-repaint-comparison]]
- **Tests:**
    - `tests/unit/api/test_repaint_comparison.py::test_a_later_instant_that_is_earlier_is_refused`
    - `tests/unit/api/test_repaint_comparison.py::test_a_missing_snapshot_is_a_404`
    - `tests/unit/api/test_repaint_comparison.py::test_a_missing_snapshot_refuses`
    - `tests/unit/api/test_repaint_comparison.py::test_a_version_difference_is_reported_not_refused`
    - `tests/unit/api/test_repaint_comparison.py::test_a_zero_width_channel_reports_no_ratio_rather_than_infinity`
    - `tests/unit/api/test_repaint_comparison.py::test_an_inverted_request_is_refused_over_http`
    - `tests/unit/api/test_repaint_comparison.py::test_every_comparison_declares_itself_research_only`
    - `tests/unit/api/test_repaint_comparison.py::test_no_hindsight_measures_model_drift_alone`
    - `tests/unit/api/test_repaint_comparison.py::test_the_centre_movement_is_also_a_share_of_the_channels_width`
    - `tests/unit/api/test_repaint_comparison.py::test_the_comparison_carries_both_channels_and_their_difference`
    - `tests/unit/api/test_repaint_comparison.py::test_the_comparison_is_reachable_over_http`
    - `tests/unit/api/test_repaint_comparison.py::test_the_hindsight_span_is_stated`
    - `tests/unit/api/test_repaint_comparison.py::test_the_signal_path_does_not_import_the_comparison`
- **Code:**
    - `src/channelflow/api/comparison.py`
    - `src/channelflow/api/routes.py`
    - `src/channelflow/api/schemas.py`
- **Outcomes:** [[OUT-2026-09-09-implement-repaint-comparison]], [[OUT-2026-09-09-plan-repaint-comparison]], [[OUT-2026-09-09-spec-repaint-comparison]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
