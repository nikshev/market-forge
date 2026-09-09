---
id: REQ-EXP-001
title: Channel model comparison
type: experiment
prd_ref: "EXP-001 Channel model comparison"
prd_lines: "5050-5069"
phase: null
status: implemented
depends_on: ["REQ-CHAN-001", "REQ-BT-001", "REQ-WP-010"]
tags: []
---

## Requirement

Compare:

- rolling OLS std bands;
- rolling OLS residual quantiles;
- Huber + MAD;
- quantile regression;
- Kalman.

Metrics:

- next-H coverage;
- boundary interaction stability;
- number of false “perfect” historical touches;
- slope stability;
- width stability;
- computational cost;
- rejection strategy expectancy OOS.

## Acceptance

- next-H coverage;
- boundary interaction stability;
- number of false “perfect” historical touches;
- slope stability;
- width stability;
- computational cost;
- rejection strategy expectancy OOS.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-034-channel-comparison]]
- **Tests:**
    - `tests/unit/research/test_channel_comparison.py::test_a_degenerate_channel_has_no_coverage_rather_than_perfect_coverage`
    - `tests/unit/research/test_channel_comparison.py::test_a_model_that_cannot_fit_is_reported_and_does_not_stop_the_others`
    - `tests/unit/research/test_channel_comparison.py::test_a_model_whose_outcomes_are_all_ambiguous_reports_no_expectancy`
    - `tests/unit/research/test_channel_comparison.py::test_a_model_with_no_setups_reports_absent_expectancy`
    - `tests/unit/research/test_channel_comparison.py::test_a_repainted_touch_is_counted_as_false`
    - `tests/unit/research/test_channel_comparison.py::test_a_series_too_short_for_the_longest_lookback_is_refused`
    - `tests/unit/research/test_channel_comparison.py::test_a_wider_band_covers_more`
    - `tests/unit/research/test_channel_comparison.py::test_all_five_models_are_compared`
    - `tests/unit/research/test_channel_comparison.py::test_coverage_looks_forward_from_each_fit`
    - `tests/unit/research/test_channel_comparison.py::test_every_model_sees_the_same_bars_and_split`
    - `tests/unit/research/test_channel_comparison.py::test_expectancy_counts_only_out_of_sample_confirmations`
    - `tests/unit/research/test_channel_comparison.py::test_expectancy_without_costs_is_refused`
    - `tests/unit/research/test_channel_comparison.py::test_stability_is_the_dispersion_not_the_average`
    - `tests/unit/research/test_channel_comparison.py::test_the_cost_figure_is_deterministic`
    - `tests/unit/research/test_channel_comparison.py::test_the_cost_figure_separates_the_expensive_model_from_the_cheap_one`
    - `tests/unit/research/test_channel_comparison.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/channels/rolling_ols.py`
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/channel_comparison.py`
- **Outcomes:** [[OUT-2026-09-09-implement-channel-comparison]], [[OUT-2026-09-09-plan-channel-comparison]], [[OUT-2026-09-09-spec-channel-comparison]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
