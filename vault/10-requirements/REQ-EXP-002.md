---
id: REQ-EXP-002
title: Lookback sensitivity
type: experiment
prd_ref: "EXP-002 Lookback sensitivity"
prd_lines: "5070-5082"
phase: null
status: implemented
depends_on: ["REQ-EXP-001", "REQ-BT-001"]
tags: []
---

## Requirement

Lookbacks:

- 40;
- 60;
- 80;
- 100;
- 150;
- 200 bars.

Do not select solely on maximum PnL; evaluate stability plateau.

## Acceptance

- lookbacks 40/60/80/100/150/200 bars are compared;
- lookback selection is not based solely on maximum PnL;
- a stability plateau across lookbacks is evaluated and reported.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-035-lookback-sensitivity]]
- **Tests:**
    - `tests/unit/research/test_lookback_sensitivity.py::test_a_jagged_sweep_has_no_plateau`
    - `tests/unit/research/test_lookback_sensitivity.py::test_a_lookback_the_series_cannot_hold_is_reported_and_the_rest_still_run`
    - `tests/unit/research/test_lookback_sensitivity.py::test_a_recommendation_carries_the_plateau_it_came_from`
    - `tests/unit/research/test_lookback_sensitivity.py::test_a_single_lookback_is_not_a_plateau`
    - `tests/unit/research/test_lookback_sensitivity.py::test_a_sweep_without_costs_is_refused`
    - `tests/unit/research/test_lookback_sensitivity.py::test_a_wider_tolerance_never_shrinks_the_plateau`
    - `tests/unit/research/test_lookback_sensitivity.py::test_all_six_lookbacks_are_swept`
    - `tests/unit/research/test_lookback_sensitivity.py::test_an_absent_value_splits_a_plateau_rather_than_being_skipped`
    - `tests/unit/research/test_lookback_sensitivity.py::test_equally_wide_plateaus_are_broken_by_a_declared_rule`
    - `tests/unit/research/test_lookback_sensitivity.py::test_the_plateau_is_the_widest_run_within_the_tolerance`
    - `tests/unit/research/test_lookback_sensitivity.py::test_the_recommendation_comes_from_the_plateau_not_the_peak`
    - `tests/unit/research/test_lookback_sensitivity.py::test_the_recommendation_is_the_middle_of_the_plateau_not_its_edge`
    - `tests/unit/research/test_lookback_sensitivity.py::test_two_sweeps_produce_equal_reports`
    - `tests/unit/research/test_lookback_sensitivity.py::test_with_no_plateau_nothing_is_recommended_and_the_peak_is_not_substituted`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/lookback_sensitivity.py`
- **Outcomes:** [[OUT-2026-09-09-implement-lookback-sensitivity]], [[OUT-2026-09-09-plan-lookback-sensitivity]], [[OUT-2026-09-09-spec-lookback-sensitivity]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
