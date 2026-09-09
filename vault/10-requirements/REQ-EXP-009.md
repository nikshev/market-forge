---
id: REQ-EXP-009
title: Forecast corridor calibration
type: experiment
prd_ref: "EXP-009 Forecast corridor calibration"
prd_lines: "5146-5157"
phase: null
status: implemented
depends_on: ["REQ-WP-006", "REQ-CHAN-001"]
tags: []
---

## Requirement

Compare:

- empirical residual quantile;
- parametric std band;
- conformal-adjusted interval.

Metric:

- target coverage with narrowest stable interval.

## Acceptance

- target coverage with narrowest stable interval.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-042-corridor-calibration]]
- **Tests:**
    - `tests/unit/research/test_corridor_calibration.py::test_a_series_too_short_is_refused`
    - `tests/unit/research/test_corridor_calibration.py::test_a_tie_on_width_is_broken_by_name`
    - `tests/unit/research/test_corridor_calibration.py::test_a_wider_target_needs_a_wider_corridor`
    - `tests/unit/research/test_corridor_calibration.py::test_all_three_methods_are_measured`
    - `tests/unit/research/test_corridor_calibration.py::test_coverage_is_reported_by_fold_not_pooled`
    - `tests/unit/research/test_corridor_calibration.py::test_only_the_prds_coverage_levels_are_accepted`
    - `tests/unit/research/test_corridor_calibration.py::test_stability_is_per_fold_not_on_average`
    - `tests/unit/research/test_corridor_calibration.py::test_the_conformal_corridor_adapts_where_the_others_do_not`
    - `tests/unit/research/test_corridor_calibration.py::test_the_conformal_corridor_does_not_calibrate_on_its_own_outcome`
    - `tests/unit/research/test_corridor_calibration.py::test_the_forecast_centre_follows_the_channels_slope`
    - `tests/unit/research/test_corridor_calibration.py::test_the_narrowest_stable_corridor_wins_not_the_narrowest`
    - `tests/unit/research/test_corridor_calibration.py::test_two_runs_produce_equal_reports`
    - `tests/unit/research/test_corridor_calibration.py::test_with_nothing_stable_there_is_no_winner`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/corridor_calibration.py`
- **Outcomes:** [[OUT-2026-09-09-implement-corridor-calibration]], [[OUT-2026-09-09-plan-corridor-calibration]], [[OUT-2026-09-09-spec-corridor-calibration]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
