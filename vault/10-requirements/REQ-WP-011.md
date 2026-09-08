---
id: REQ-WP-011
title: OFI/LOB features
type: work-package
prd_ref: "WP-011 OFI/LOB features"
prd_lines: "7011-7019"
phase: null
status: implemented
depends_on: ["REQ-WP-004", "REQ-WP-005"]
tags: []
---

## Requirement

- QI;
- depth imbalance;
- microprice;
- OFI;
- CVD;
- persistence.

## Acceptance

- queue imbalance (QI) is computed;
- depth imbalance is computed;
- microprice is computed;
- OFI is computed;
- CVD is computed;
- wall persistence/cancellation is tracked.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-011-ofi-lob-features]]
- **Tests:**
    - `tests/unit/features/test_flow.py::test_a_window_with_no_volume_has_no_normalized_delta`
    - `tests/unit/features/test_flow.py::test_acceleration_compares_a_window_with_the_one_before_it`
    - `tests/unit/features/test_flow.py::test_an_unknown_aggressor_counts_as_volume_and_as_neither_side`
    - `tests/unit/features/test_flow.py::test_cumulative_delta_is_the_running_sum`
    - `tests/unit/features/test_flow.py::test_delta_is_buy_notional_minus_sell_notional`
    - `tests/unit/features/test_flow.py::test_no_divergence_feature_is_exposed`
    - `tests/unit/features/test_flow.py::test_normalized_delta_is_delta_over_the_window_volume`
    - `tests/unit/features/test_flow.py::test_the_cvd_slope_is_the_change_across_the_window_per_second`
    - `tests/unit/features/test_flow.py::test_trades_must_arrive_in_event_time_order`
    - `tests/unit/features/test_instant.py::test_a_band_imbalance_reflects_lopsided_depth`
    - `tests/unit/features/test_instant.py::test_depth_imbalance_deepens_as_more_levels_are_counted`
    - `tests/unit/features/test_instant.py::test_depth_imbalance_over_a_symmetric_book_is_zero[1-0.0]`
    - `tests/unit/features/test_instant.py::test_depth_imbalance_over_a_symmetric_book_is_zero[2-0.0]`
    - `tests/unit/features/test_instant.py::test_depth_imbalance_over_a_symmetric_book_is_zero[4-0.0]`
    - `tests/unit/features/test_instant.py::test_depth_imbalance_over_basis_point_bands`
    - `tests/unit/features/test_instant.py::test_every_instant_feature_refuses_an_invalid_book`
    - `tests/unit/features/test_instant.py::test_queue_imbalance_at_the_touch`
    - `tests/unit/features/test_instant.py::test_queue_imbalance_is_zero_when_the_queues_match`
    - `tests/unit/features/test_instant.py::test_queue_imbalance_refuses_an_empty_side`
    - `tests/unit/features/test_instant.py::test_queue_imbalance_refuses_two_zero_sized_touches`
    - `tests/unit/features/test_instant.py::test_the_microprice_equals_the_mid_when_the_queues_match`
    - `tests/unit/features/test_instant.py::test_the_microprice_leans_away_from_the_larger_queue`
    - `tests/unit/features/test_instant.py::test_the_microprice_mid_spread_is_reported_in_basis_points`
    - `tests/unit/features/test_ofi.py::test_a_falling_bid_price_removes_the_old_size`
    - `tests/unit/features/test_ofi.py::test_a_rising_ask_price_adds_back_the_old_size`
    - `tests/unit/features/test_ofi.py::test_a_rising_bid_price_contributes_its_whole_new_size`
    - `tests/unit/features/test_ofi.py::test_a_window_sums_the_increments_inside_it`
    - `tests/unit/features/test_ofi.py::test_an_empty_window_is_distinguishable_from_a_balanced_one`
    - `tests/unit/features/test_ofi.py::test_an_unchanged_bid_price_contributes_the_size_change`
    - `tests/unit/features/test_ofi.py::test_both_sides_combine_in_one_increment`
    - `tests/unit/features/test_ofi.py::test_every_prd_window_length_is_available`
    - `tests/unit/features/test_ofi.py::test_no_increment_is_computed_across_a_gap`
    - `tests/unit/features/test_ofi.py::test_observations_must_arrive_in_event_time_order`
    - `tests/unit/features/test_ofi.py::test_the_ask_side_enters_with_the_opposite_sign`
    - `tests/unit/features/test_ofi.py::test_the_first_observation_produces_no_increment`
    - `tests/unit/features/test_registry.py::test_a_name_matches_its_key`
    - `tests/unit/features/test_registry.py::test_a_registration_cannot_be_edited_after_the_fact`
    - `tests/unit/features/test_registry.py::test_a_registration_states_point_in_time_safety_explicitly`
    - `tests/unit/features/test_registry.py::test_every_exposed_feature_is_registered`
    - `tests/unit/features/test_registry.py::test_no_required_field_is_blank`
    - `tests/unit/features/test_registry.py::test_the_features_package_cannot_consult_a_clock`
    - `tests/unit/features/test_registry.py::test_the_registry_is_not_empty`
    - `tests/unit/features/test_walls.py::test_a_decrease_matched_by_trades_is_recorded_as_executed`
    - `tests/unit/features/test_walls.py::test_a_decrease_with_no_trades_is_recorded_as_cancelled`
    - `tests/unit/features/test_walls.py::test_a_finished_wall_is_kept_and_never_rewritten`
    - `tests/unit/features/test_walls.py::test_a_level_far_larger_than_its_neighbours_becomes_a_wall`
    - `tests/unit/features/test_walls.py::test_a_wall_that_grows_again_is_a_refill_not_a_new_wall`
    - `tests/unit/features/test_walls.py::test_an_ordinary_level_is_not_a_wall`
    - `tests/unit/features/test_walls.py::test_executed_never_exceeds_what_actually_traded_there`
    - `tests/unit/features/test_walls.py::test_persistence_is_measured_in_event_time`
    - `tests/unit/features/test_walls.py::test_the_anomaly_threshold_is_configurable`
    - `tests/unit/features/test_walls.py::test_trades_at_another_price_are_not_attributed_to_this_wall`
- **Code:**
    - `src/channelflow/features/__init__.py`
    - `src/channelflow/features/flow.py`
    - `src/channelflow/features/instant.py`
    - `src/channelflow/features/ofi.py`
    - `src/channelflow/features/registry.py`
    - `src/channelflow/features/walls.py`
- **Outcomes:** [[OUT-2026-09-08-implement-ofi-lob-features]], [[OUT-2026-09-08-plan-ofi-lob-features]], [[OUT-2026-09-08-spec-ofi-lob-features]], [[OUT-2026-09-08-tasks-ofi-lob-features]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
