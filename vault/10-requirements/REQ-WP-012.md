---
id: REQ-WP-012
title: Volume profile
type: work-package
prd_ref: "WP-012 Volume profile"
prd_lines: "7020-7026"
phase: null
status: implemented
depends_on: ["REQ-WP-003", "REQ-WP-009"]
tags: []
---

## Requirement

- trade-level bins;
- POC/VAH/VAL;
- HVN/LVN;
- chart plugin.

## Acceptance

- volume is binned at the trade level;
- POC/VAH/VAL are computed;
- HVN/LVN are identified;
- a chart plugin renders the profile.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-017-volume-profile]]
- **Tests:**
    - `tests/unit/volume/test_nodes.py::test_a_gap_is_a_low_volume_node`
    - `tests/unit/volume/test_nodes.py::test_a_shelf_is_a_high_volume_node`
    - `tests/unit/volume/test_nodes.py::test_a_uniform_profile_has_no_nodes`
    - `tests/unit/volume/test_nodes.py::test_channel_boundaries_are_matched_to_the_nodes_they_fall_inside`
    - `tests/unit/volume/test_nodes.py::test_nodes_are_relative_to_neighbours_not_to_the_whole_profile`
    - `tests/unit/volume/test_nodes.py::test_the_thresholds_are_configurable`
    - `tests/unit/volume/test_nodes.py::test_the_volume_package_cannot_consult_a_clock`
    - `tests/unit/volume/test_profile.py::test_a_single_price_profile_is_its_own_value_area`
    - `tests/unit/volume/test_profile.py::test_a_tie_goes_to_the_lower_price_and_is_recorded`
    - `tests/unit/volume/test_profile.py::test_a_trade_on_a_boundary_falls_in_the_upper_bin`
    - `tests/unit/volume/test_profile.py::test_an_empty_window_refuses`
    - `tests/unit/volume/test_profile.py::test_an_unreachable_target_takes_the_whole_profile_and_says_so`
    - `tests/unit/volume/test_profile.py::test_bins_hold_the_volume_that_traded_in_them`
    - `tests/unit/volume/test_profile.py::test_building_is_deterministic`
    - `tests/unit/volume/test_profile.py::test_sides_come_from_the_aggressor_never_from_bar_direction`
    - `tests/unit/volume/test_profile.py::test_the_poc_is_the_busiest_bin`
    - `tests/unit/volume/test_profile.py::test_the_value_area_holds_at_least_the_configured_share`
    - `tests/unit/volume/test_profile.py::test_the_value_area_is_contiguous_and_contains_the_poc`
    - `tests/unit/volume/test_profile.py::test_the_value_area_is_contiguous_on_a_bimodal_profile`
    - `tests/unit/volume/test_profile.py::test_vah_and_val_bound_the_value_area`
    - `tests/unit/volume/test_shape.py::test_a_non_positive_price_has_no_distance`
    - `tests/unit/volume/test_shape.py::test_a_single_price_profile_has_zero_entropy`
    - `tests/unit/volume/test_shape.py::test_a_symmetric_profile_has_no_skew`
    - `tests/unit/volume/test_shape.py::test_distances_are_in_basis_points`
    - `tests/unit/volume/test_shape.py::test_entropy_is_lower_when_volume_is_concentrated`
    - `tests/unit/volume/test_shape.py::test_skew_is_positive_with_more_volume_above`
- **Code:**
    - `apps/web/src/__tests__/volumeProfile.test.ts`
    - `apps/web/src/volumeProfile.ts`
    - `src/channelflow/volume/__init__.py`
    - `src/channelflow/volume/nodes.py`
    - `src/channelflow/volume/profile.py`
    - `src/channelflow/volume/shape.py`
- **Outcomes:** [[OUT-2026-09-08-implement-volume-profile]], [[OUT-2026-09-08-spec-volume-profile]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
