---
id: REQ-WP-013
title: Derivatives
type: work-package
prd_ref: "WP-013 Derivatives"
prd_lines: "7027-7032"
phase: null
status: implemented
depends_on: ["REQ-WP-003"]
tags: []
---

## Requirement

- funding/OI/basis/liquidations;
- z-scores;
- state joins.

## Acceptance

- funding, OI, basis, and liquidations are ingested;
- z-scores are computed for these features;
- derivatives state joins are performed.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-016-derivatives]]
- **Tests:**
    - `tests/unit/derivatives/test_funding.py::test_a_constant_series_has_no_z_score`
    - `tests/unit/derivatives/test_funding.py::test_a_short_window_refuses`
    - `tests/unit/derivatives/test_funding.py::test_acceleration_is_signed`
    - `tests/unit/derivatives/test_funding.py::test_acceleration_needs_three_intervals`
    - `tests/unit/derivatives/test_funding.py::test_an_unsettled_rate_is_not_used_at_t`
    - `tests/unit/derivatives/test_funding.py::test_no_settled_interval_means_no_rate`
    - `tests/unit/derivatives/test_funding.py::test_the_z_score_uses_only_settled_rates`
    - `tests/unit/derivatives/test_liquidations.py::test_a_spike_after_the_instant_is_not_counted`
    - `tests/unit/derivatives/test_liquidations.py::test_a_zero_notional_print_counts_as_an_event`
    - `tests/unit/derivatives/test_liquidations.py::test_clusters_group_by_relative_price_bucket`
    - `tests/unit/derivatives/test_liquidations.py::test_clusters_of_an_impossible_reference_are_empty`
    - `tests/unit/derivatives/test_liquidations.py::test_intensity_is_absent_on_no_volume`
    - `tests/unit/derivatives/test_liquidations.py::test_no_spike_is_absent_not_infinite`
    - `tests/unit/derivatives/test_liquidations.py::test_sides_are_totalled_separately`
    - `tests/unit/derivatives/test_liquidations.py::test_the_derivatives_package_cannot_consult_a_clock`
    - `tests/unit/derivatives/test_liquidations.py::test_the_imbalance_is_absent_when_nothing_was_liquidated`
    - `tests/unit/derivatives/test_liquidations.py::test_the_imbalance_is_hand_computable`
    - `tests/unit/derivatives/test_liquidations.py::test_the_window_excludes_what_is_outside_it`
    - `tests/unit/derivatives/test_liquidations.py::test_time_since_a_spike_is_event_time`
    - `tests/unit/derivatives/test_openinterest.py::test_a_flat_leg_is_undetermined`
    - `tests/unit/derivatives/test_openinterest.py::test_a_missing_leg_is_absent_not_zero`
    - `tests/unit/derivatives/test_openinterest.py::test_a_window_with_nothing_before_it_has_no_change`
    - `tests/unit/derivatives/test_openinterest.py::test_base_only_states_are_skipped`
    - `tests/unit/derivatives/test_openinterest.py::test_basis_is_relative_to_spot`
    - `tests/unit/derivatives/test_openinterest.py::test_change_is_measured_from_before_the_window`
    - `tests/unit/derivatives/test_openinterest.py::test_each_quadrant_is_labelled[-1.0--1.0-long liquidation/de-risk candidate]`
    - `tests/unit/derivatives/test_openinterest.py::test_each_quadrant_is_labelled[-1.0-1.0-new shorts / risk build candidate]`
    - `tests/unit/derivatives/test_openinterest.py::test_each_quadrant_is_labelled[1.0--1.0-short-covering candidate]`
    - `tests/unit/derivatives/test_openinterest.py::test_each_quadrant_is_labelled[1.0-1.0-new risk entering / trend participation candidate]`
    - `tests/unit/derivatives/test_openinterest.py::test_oi_z_refuses_a_short_window`
    - `tests/unit/derivatives/test_openinterest.py::test_the_mark_premium_is_relative_to_the_index`
    - `tests/unit/derivatives/test_openinterest.py::test_the_ratio_is_absent_on_no_volume`
    - `tests/unit/derivatives/test_openinterest.py::test_the_regime_names_keep_the_prds_hedge`
    - `tests/unit/derivatives/test_state.py::test_a_later_ingest_time_wins_at_the_same_event_time`
    - `tests/unit/derivatives/test_state.py::test_a_tie_on_both_times_is_refused`
    - `tests/unit/derivatives/test_state.py::test_no_state_at_all_is_a_named_refusal`
    - `tests/unit/derivatives/test_state.py::test_the_join_never_returns_a_later_state`
- **Outcomes:** [[OUT-2026-09-08-implement-derivatives]], [[OUT-2026-09-08-plan-derivatives]], [[OUT-2026-09-08-spec-derivatives]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
