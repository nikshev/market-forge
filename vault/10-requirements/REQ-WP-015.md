---
id: REQ-WP-015
title: Uniswap v3 adapter
type: work-package
prd_ref: "WP-015 Uniswap v3 adapter"
prd_lines: "7041-7048"
phase: null
status: implemented
depends_on: ["REQ-WP-014"]
tags: []
---

## Requirement

- pool math;
- swap decode;
- mint/burn;
- tick state;
- depth simulation.

## Acceptance

- pool math is implemented;
- swaps are decoded;
- mint/burn events are decoded;
- tick state is tracked;
- depth is simulated.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-021-uniswap-v3]]
- **Tests:**
    - `tests/unit/dex/test_depth.py::test_a_negative_band_is_refused`
    - `tests/unit/dex/test_depth.py::test_a_pool_with_no_active_liquidity_cannot_be_moved`
    - `tests/unit/dex/test_depth.py::test_a_pool_with_no_price_is_refused`
    - `tests/unit/dex/test_depth.py::test_a_symmetric_pool_reports_no_asymmetry`
    - `tests/unit/dex/test_depth.py::test_a_target_beyond_known_liquidity_is_unreachable`
    - `tests/unit/dex/test_depth.py::test_an_unreachable_quote_still_reports_how_far_it_got`
    - `tests/unit/dex/test_depth.py::test_both_directions_are_computed`
    - `tests/unit/dex/test_depth.py::test_crossing_a_tick_changes_the_liquidity_used`
    - `tests/unit/dex/test_depth.py::test_depth_rises_with_distance`
    - `tests/unit/dex/test_depth.py::test_single_range_depth_matches_the_closed_form`
    - `tests/unit/dex/test_depth.py::test_the_curve_covers_the_bands_the_prd_names`
    - `tests/unit/dex/test_depth.py::test_the_curve_reports_where_the_pool_is_asymmetric`
    - `tests/unit/dex/test_depth.py::test_zero_basis_points_costs_nothing`
    - `tests/unit/dex/test_math.py::test_a_non_positive_price_is_refused`
    - `tests/unit/dex/test_math.py::test_a_price_round_trips_through_the_fixed_point_encoding`
    - `tests/unit/dex/test_math.py::test_a_tick_outside_the_pools_bounds_is_refused`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[-100000]`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[-1]`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[-887000]`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[0]`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[100000]`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[1]`
    - `tests/unit/dex/test_math.py::test_a_tick_round_trips_through_price[887000]`
    - `tests/unit/dex/test_math.py::test_decimals_are_applied_to_the_human_price`
    - `tests/unit/dex/test_math.py::test_one_tick_is_one_basis_point`
    - `tests/unit/dex/test_math.py::test_sqrt_price_x96_is_the_square_of_the_fixed_point_value`
    - `tests/unit/dex/test_math.py::test_tick_from_price_floors_rather_than_rounds`
    - `tests/unit/dex/test_math.py::test_tick_zero_is_price_one`
    - `tests/unit/dex/test_pool.py::test_a_burn_reverses_a_mint_exactly`
    - `tests/unit/dex/test_pool.py::test_a_burn_that_exceeds_the_liquidity_is_refused`
    - `tests/unit/dex/test_pool.py::test_a_divergence_names_the_fields_and_leaves_the_state_alone`
    - `tests/unit/dex/test_pool.py::test_a_duplicate_log_is_refused`
    - `tests/unit/dex/test_pool.py::test_a_matching_contract_read_raises_no_incident`
    - `tests/unit/dex/test_pool.py::test_a_mint_adds_at_the_lower_tick_and_subtracts_at_the_upper`
    - `tests/unit/dex/test_pool.py::test_a_range_away_from_the_current_tick_does_not`
    - `tests/unit/dex/test_pool.py::test_a_range_spanning_the_current_tick_changes_active_liquidity`
    - `tests/unit/dex/test_pool.py::test_collect_leaves_liquidity_untouched`
    - `tests/unit/dex/test_pool.py::test_events_are_applied_in_canonical_order_not_arrival_order`
    - `tests/unit/dex/test_pool.py::test_rebuild_does_not_mutate_the_state_it_was_given`
    - `tests/unit/dex/test_pool.py::test_the_dex_package_cannot_consult_a_clock_or_open_a_socket`
    - `tests/unit/dex/test_pool.py::test_the_upper_tick_is_exclusive`
    - `tests/unit/dex/test_pool.py::test_transaction_index_breaks_a_tie_within_a_block`
- **Code:**
    - `src/channelflow/dex/__init__.py`
    - `src/channelflow/dex/depth.py`
    - `src/channelflow/dex/events.py`
    - `src/channelflow/dex/math.py`
    - `src/channelflow/dex/pool.py`
- **Outcomes:** [[OUT-2026-09-08-implement-uniswap-v3]], [[OUT-2026-09-08-plan-uniswap-v3]], [[OUT-2026-09-08-spec-uniswap-v3]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
