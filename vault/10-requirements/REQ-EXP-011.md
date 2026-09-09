---
id: REQ-EXP-011
title: Structural extremum detector
type: experiment
prd_ref: "EXP-011 Structural extremum detector"
prd_lines: "5163-5180"
phase: null
status: implemented
depends_on: ["REQ-WP-019", "REQ-BT-001", "REQ-CHAN-001"]
tags: []
---

## Requirement

Compare non-repainting confirmed swing methods:

- fixed-bps directional change;
- ATR-adaptive directional change;
- realized-vol adaptive directional change;
- channel-width adaptive directional change;
- hybrid threshold.

Metrics:

- confirmation lag;
- extrema per 1000 bars;
- prominence;
- stability across volatility regimes;
- downstream setup expectancy.

## Acceptance

- confirmation lag;
- extrema per 1000 bars;
- prominence;
- stability across volatility regimes;
- downstream setup expectancy.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-044-extremum-detectors]]
- **Tests:**
    - `tests/unit/research/test_extremum_detectors.py::test_a_confirmation_always_lags_its_extremum`
    - `tests/unit/research/test_extremum_detectors.py::test_a_fixed_threshold_is_less_stable_across_regimes_than_an_adaptive_one`
    - `tests/unit/research/test_extremum_detectors.py::test_a_method_that_confirms_nothing_says_so`
    - `tests/unit/research/test_extremum_detectors.py::test_all_five_methods_are_compared`
    - `tests/unit/research/test_extremum_detectors.py::test_an_extremum_belongs_to_the_regime_it_was_confirmed_in`
    - `tests/unit/research/test_extremum_detectors.py::test_every_metric_is_reported_for_a_method_that_fired`
    - `tests/unit/research/test_extremum_detectors.py::test_extrema_are_attributed_to_both_regimes`
    - `tests/unit/research/test_extremum_detectors.py::test_nothing_is_ranked`
    - `tests/unit/research/test_extremum_detectors.py::test_the_channel_mode_fires_when_a_channel_is_supplied`
    - `tests/unit/research/test_extremum_detectors.py::test_the_channel_mode_needs_a_channel_and_says_so`
    - `tests/unit/research/test_extremum_detectors.py::test_the_channel_mode_uses_the_channels_own_width`
    - `tests/unit/research/test_extremum_detectors.py::test_the_comparison_without_costs_is_refused`
    - `tests/unit/research/test_extremum_detectors.py::test_the_downstream_expectancy_is_after_costs`
    - `tests/unit/research/test_extremum_detectors.py::test_the_median_split_divides_the_series_in_half`
    - `tests/unit/research/test_extremum_detectors.py::test_the_regime_ratio_is_the_busier_over_the_quieter`
    - `tests/unit/research/test_extremum_detectors.py::test_the_regimes_are_split_at_the_series_own_median`
    - `tests/unit/research/test_extremum_detectors.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/extrema/detector.py`
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/extremum_detectors.py`
- **Outcomes:** [[OUT-2026-09-09-implement-extremum-detectors]], [[OUT-2026-09-09-plan-extremum-detectors]], [[OUT-2026-09-09-spec-extremum-detectors]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
