---
id: REQ-WP-019
title: Price extrema / turning points
type: work-package
prd_ref: "WP-019 Price extrema / turning points"
prd_lines: "7072-7099"
phase: null
status: tested
depends_on: []
tags: []
---

## Requirement

Implement in this order:

1. research-only symmetric `k`-neighborhood labels;
2. directional-change live baseline;
3. adaptive threshold interface;
4. causal local-polynomial slope/curvature;
5. optional Kalman filtered slope;
6. `ExtremumCandidate`, `TurningPointForecast`, `ConfirmedExtremum`, outcome models;
7. Kafka topics and storage adapters;
8. chart overlays and `AS-SEEN-THEN` semantics;
9. structural turning-point score;
10. point-in-time dataset targets for max/min/no-turn;
11. direct logistic/boosted baseline;
12. GMDH forward-path derivative experiment;
13. root-stability analysis;
14. Telegram alert integration behind a feature flag.

Done when:

- future-bar invariance test passes;
- confirmation legality test passes;
- replay parity passes;
- direct baseline metrics exist;
- derivative experiment can return `NO_EDGE` without blocking product completion.

## Acceptance

- future-bar invariance test passes;
- confirmation legality test passes;
- replay parity passes;
- direct baseline metrics exist;
- derivative experiment can return `NO_EDGE` without blocking product completion.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Tests:**
    - `tests/unit/extrema/test_directional_change.py::test_a_high_is_dated_to_its_peak_and_known_at_the_crossing`
    - `tests/unit/extrema/test_directional_change.py::test_a_low_is_detected_symmetrically`
    - `tests/unit/extrema/test_directional_change.py::test_a_record_cannot_be_edited_after_the_fact`
    - `tests/unit/extrema/test_directional_change.py::test_a_record_claiming_to_be_known_before_it_happened_cannot_be_built`
    - `tests/unit/extrema/test_directional_change.py::test_a_running_high_that_never_reverses_far_enough_confirms_nothing`
    - `tests/unit/extrema/test_directional_change.py::test_known_at_is_never_before_extremum_time_over_a_long_series`
    - `tests/unit/extrema/test_directional_change.py::test_the_confirmation_lag_is_the_distance_between_them`
    - `tests/unit/extrema/test_directional_change.py::test_the_threshold_in_force_is_stored_on_the_confirmation`
    - `tests/unit/extrema/test_non_repainting.py::test_a_appending_future_bars_changes_no_finalized_output`
    - `tests/unit/extrema/test_non_repainting.py::test_b_an_invalidated_candidate_keeps_its_original_record`
    - `tests/unit/extrema/test_non_repainting.py::test_c_known_at_is_never_before_the_extremum`
    - `tests/unit/extrema/test_non_repainting.py::test_d_a_centered_transform_is_refused_by_the_production_path`
    - `tests/unit/extrema/test_non_repainting.py::test_e_a_replayed_stream_matches_the_live_run_exactly`
    - `tests/unit/extrema/test_non_repainting.py::test_the_extrema_package_cannot_consult_a_clock`
    - `tests/unit/extrema/test_prominence.py::test_a_swing_below_the_minimum_prominence_is_not_confirmed`
    - `tests/unit/extrema/test_prominence.py::test_prominence_is_the_excursion_from_the_baseline`
    - `tests/unit/extrema/test_prominence.py::test_the_atr_criterion_applies_only_when_atr_is_known`
    - `tests/unit/extrema/test_prominence.py::test_the_first_extremum_has_no_predecessor_to_be_too_close_to`
    - `tests/unit/extrema/test_prominence.py::test_two_extrema_too_close_together_are_rejected`
    - `tests/unit/extrema/test_thresholds.py::test_a_threshold_uses_only_bars_at_or_before_the_instant`
    - `tests/unit/extrema/test_thresholds.py::test_the_atr_mode_rises_with_volatility`
    - `tests/unit/extrema/test_thresholds.py::test_the_channel_mode_refuses_without_a_channel`
    - `tests/unit/extrema/test_thresholds.py::test_the_channel_width_mode_is_a_fraction_of_the_width`
    - `tests/unit/extrema/test_thresholds.py::test_the_fixed_mode_returns_its_configured_value`
    - `tests/unit/extrema/test_thresholds.py::test_the_hybrid_is_the_maximum_and_never_below_the_floor`
    - `tests/unit/extrema/test_thresholds.py::test_the_hybrid_survives_a_component_without_history`
    - `tests/unit/extrema/test_thresholds.py::test_the_realized_vol_mode_rises_with_volatility`
    - `tests/unit/extrema/test_thresholds.py::test_too_little_history_refuses_rather_than_approximating`
- **Code:**
    - `src/channelflow/extrema/__init__.py`
    - `src/channelflow/extrema/causality.py`
    - `src/channelflow/extrema/detector.py`
    - `src/channelflow/extrema/models.py`
    - `src/channelflow/extrema/prominence.py`
    - `src/channelflow/extrema/thresholds.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-points]], [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
