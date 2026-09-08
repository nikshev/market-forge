---
id: REQ-WP-019
title: Price extrema / turning points
type: work-package
prd_ref: "WP-019 Price extrema / turning points"
prd_lines: "7072-7099"
phase: null
status: implemented
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
- **Specs:** [[SPEC-014-turning-points]], [[SPEC-024-turning-derivative]]
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
    - `tests/unit/turning/test_direct.py::test_a_fold_whose_target_never_occurs_is_reported_not_scored`
    - `tests/unit/turning/test_direct.py::test_a_learnable_target_beats_the_base_rate`
    - `tests/unit/turning/test_direct.py::test_a_row_missing_a_declared_feature_is_refused`
    - `tests/unit/turning/test_direct.py::test_a_signal_free_target_reports_that_it_does_not_beat_the_base_rate`
    - `tests/unit/turning/test_direct.py::test_features_are_read_in_the_declared_order_not_the_dicts`
    - `tests/unit/turning/test_direct.py::test_no_fold_is_fitted_and_scored_on_the_same_row`
    - `tests/unit/turning/test_direct.py::test_the_aggregate_is_weighted_by_rows_not_by_fold_count`
    - `tests/unit/turning/test_direct.py::test_the_direct_baseline_reports_metrics_per_fold_and_in_aggregate`
    - `tests/unit/turning/test_direct.py::test_the_target_column_is_the_named_class_and_nothing_else`
    - `tests/unit/turning/test_direct.py::test_the_target_is_one_of_section_23_5as_three_classes`
    - `tests/unit/turning/test_experiment.py::test_a_caller_error_still_raises`
    - `tests/unit/turning/test_experiment.py::test_a_row_without_a_forward_path_is_refused`
    - `tests/unit/turning/test_experiment.py::test_a_signal_free_experiment_returns_no_edge_and_raises_nothing`
    - `tests/unit/turning/test_experiment.py::test_an_experiment_with_an_edge_says_so`
    - `tests/unit/turning/test_experiment.py::test_every_outcome_carries_its_report_and_its_stability_metrics`
    - `tests/unit/turning/test_experiment.py::test_roots_that_no_gate_would_promote_are_reported_with_their_reasons`
    - `tests/unit/turning/test_experiment.py::test_too_little_data_is_a_verdict_not_a_crash`
    - `tests/unit/turning/test_path.py::test_a_flat_path_produces_no_candidate_rather_than_every_horizon`
    - `tests/unit/turning/test_path.py::test_a_horizon_that_is_not_positive_is_refused`
    - `tests/unit/turning/test_path.py::test_a_maximum_candidate_is_a_zero_slope_with_negative_curvature`
    - `tests/unit/turning/test_path.py::test_a_minimum_candidate_is_the_mirror_image`
    - `tests/unit/turning/test_path.py::test_a_root_at_zero_is_not_a_candidate`
    - `tests/unit/turning/test_path.py::test_a_root_outside_the_horizon_is_not_a_candidate`
    - `tests/unit/turning/test_path.py::test_a_straight_path_has_no_root`
    - `tests/unit/turning/test_path.py::test_an_inflection_is_not_a_turn`
    - `tests/unit/turning/test_path.py::test_both_roots_of_a_cubic_are_returned`
    - `tests/unit/turning/test_path.py::test_every_solved_zero_really_zeroes_the_slope`
    - `tests/unit/turning/test_path.py::test_the_excursion_is_measured_from_now_not_from_the_intercept`
    - `tests/unit/turning/test_path.py::test_the_path_and_its_derivatives_are_the_prds_own_formulas`
    - `tests/unit/turning/test_roots.py::test_every_assessment_records_the_three_section_13a12_metrics`
    - `tests/unit/turning/test_roots.py::test_the_turning_package_consults_neither_a_clock_nor_a_random_source`
- **Code:**
    - `src/channelflow/extrema/__init__.py`
    - `src/channelflow/extrema/causality.py`
    - `src/channelflow/extrema/detector.py`
    - `src/channelflow/extrema/models.py`
    - `src/channelflow/extrema/prominence.py`
    - `src/channelflow/extrema/thresholds.py`
    - `src/channelflow/models/gmdh.py`
    - `src/channelflow/turning/__init__.py`
    - `src/channelflow/turning/direct.py`
    - `src/channelflow/turning/experiment.py`
    - `src/channelflow/turning/path.py`
    - `src/channelflow/turning/roots.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-derivative]], [[OUT-2026-09-08-implement-turning-points]], [[OUT-2026-09-08-plan-turning-derivative]], [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-derivative]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
