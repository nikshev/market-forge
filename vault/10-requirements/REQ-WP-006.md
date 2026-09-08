---
id: REQ-WP-006
title: Channel baseline
type: work-package
prd_ref: "WP-006 Channel baseline"
prd_lines: "6975-6982"
phase: null
status: implemented
depends_on: ["REQ-WP-005"]
tags: []
---

## Requirement

- rolling OLS log price;
- residual quantile bands;
- normalized slope;
- quality score;
- append-only storage.

## Acceptance

- channel is computed via rolling OLS on log price;
- residual quantile bands are produced;
- a normalized slope is reported;
- a quality score is reported;
- channel snapshots are append-only storage.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-007-channel-baseline]]
- **Tests:**
    - `tests/unit/channels/test_fit.py::test_a_constructed_slope_is_recovered`
    - `tests/unit/channels/test_fit.py::test_a_flat_series_collapses_the_bands_without_dividing_by_zero`
    - `tests/unit/channels/test_fit.py::test_a_non_positive_close_refuses_and_names_the_bar`
    - `tests/unit/channels/test_fit.py::test_bands_sit_at_the_configured_residual_quantiles`
    - `tests/unit/channels/test_fit.py::test_input_order_does_not_change_the_fit`
    - `tests/unit/channels/test_fit.py::test_insufficient_history_refuses_and_says_so`
    - `tests/unit/channels/test_fit.py::test_the_centre_is_the_exponential_of_the_fitted_line_not_a_mean`
    - `tests/unit/channels/test_fit.py::test_the_same_shape_at_different_price_levels_gives_the_same_slope`
    - `tests/unit/channels/test_fit.py::test_the_snapshot_carries_its_model_identity`
    - `tests/unit/channels/test_fit.py::test_two_fits_over_the_same_data_are_identical`
    - `tests/unit/channels/test_no_lookahead.py::test_appending_future_bars_does_not_change_a_past_snapshot`
    - `tests/unit/channels/test_no_lookahead.py::test_bars_after_as_of_are_excluded_not_trusted`
    - `tests/unit/channels/test_no_lookahead.py::test_the_hard_invariant_holds`
    - `tests/unit/channels/test_no_lookahead.py::test_unfinalized_bars_are_excluded`
    - `tests/unit/channels/test_quality.py::test_a_clean_trend_outscores_noise`
    - `tests/unit/channels/test_quality.py::test_coverage_is_near_the_configured_band_width`
    - `tests/unit/channels/test_quality.py::test_the_score_names_what_produced_it`
    - `tests/unit/channels/test_quality.py::test_the_score_stays_in_range`
    - `tests/unit/channels/test_quality.py::test_unavailable_submetrics_are_omitted_not_defaulted`
    - `tests/unit/channels/test_quality.py::test_weights_are_configurable`
- **Outcomes:** [[OUT-2026-09-08-implement-channel-baseline]], [[OUT-2026-09-08-plan-channel-baseline]], [[OUT-2026-09-08-spec-channel-baseline]], [[OUT-2026-09-08-tasks-channel-baseline]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
