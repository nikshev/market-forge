---
id: REQ-EXP-013
title: GMDH derivative extrema
type: experiment
prd_ref: "EXP-013 GMDH derivative extrema"
prd_lines: "5195-5215"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Compare:

- direct classifier only;
- GMDH direct turning-point classifier;
- GMDH forward path + derivative roots;
- ensemble of direct probability + derivative root stability.

Report:

- root presence rate;
- root horizon IQR;
- turn-type agreement;
- time-to-turn MAE;
- extreme-price error;
- calibration;
- incremental expectancy after costs.

Reject the derivative method if roots are unstable or add no OOS value.

## Acceptance

- root presence rate is reported;
- root horizon IQR is reported;
- turn-type agreement is reported;
- time-to-turn MAE is reported;
- extreme-price error is reported;
- calibration is reported;
- incremental expectancy after costs is reported;
- the derivative method is rejected if roots are unstable or add no OOS value.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-046-gmdh-extrema]]
- **Tests:**
    - `tests/unit/research/test_gmdh_extrema.py::test_a_call_with_no_true_turn_is_counted_rather_than_scored`
    - `tests/unit/research/test_gmdh_extrema.py::test_a_called_row_without_an_outcome_is_refused`
    - `tests/unit/research/test_gmdh_extrema.py::test_a_classifier_arm_names_no_time_and_no_price`
    - `tests/unit/research/test_gmdh_extrema.py::test_a_derivative_arm_that_adds_nothing_is_rejected`
    - `tests/unit/research/test_gmdh_extrema.py::test_a_derivative_arm_that_adds_value_is_accepted`
    - `tests/unit/research/test_gmdh_extrema.py::test_all_four_arms_the_prd_names_are_compared`
    - `tests/unit/research/test_gmdh_extrema.py::test_both_reasons_are_reported_when_both_fail`
    - `tests/unit/research/test_gmdh_extrema.py::test_every_metric_the_prd_names_is_reported`
    - `tests/unit/research/test_gmdh_extrema.py::test_the_call_threshold_is_required_and_bounded`
    - `tests/unit/research/test_gmdh_extrema.py::test_the_economics_refuse_to_run_without_costs`
    - `tests/unit/research/test_gmdh_extrema.py::test_the_ensemble_keeps_its_classifier_half`
    - `tests/unit/research/test_gmdh_extrema.py::test_the_horizon_iqr_is_the_spread_of_the_roots_that_exist`
    - `tests/unit/research/test_gmdh_extrema.py::test_the_increment_is_measured_against_the_direct_classifier`
    - `tests/unit/research/test_gmdh_extrema.py::test_the_presence_rate_is_averaged_over_the_rows_that_had_a_root`
    - `tests/unit/research/test_gmdh_extrema.py::test_two_runs_produce_equal_reports`
    - `tests/unit/research/test_gmdh_extrema.py::test_unstable_roots_are_rejected`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/gmdh_extrema.py`
- **Outcomes:** [[OUT-2026-09-09-implement-gmdh-extrema]], [[OUT-2026-09-09-plan-gmdh-extrema]], [[OUT-2026-09-09-spec-gmdh-extrema]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
