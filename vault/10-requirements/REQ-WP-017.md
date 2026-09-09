---
id: REQ-WP-017
title: PIT dataset
type: work-package
prd_ref: "WP-017 PIT dataset"
prd_lines: "7055-7061"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

- as-of joins;
- leakage asserts;
- labels;
- purged chronological folds.

## Acceptance

- as-of joins are used to build the dataset;
- leakage assertions run against the dataset;
- labels are attached;
- folds are purged/chronological (no shuffled cross-validation).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-015-pit-dataset]]
- **Tests:**
    - `tests/unit/dataset/test_folds.py::test_a_horizon_that_purges_everything_is_refused`
    - `tests/unit/dataset/test_folds.py::test_building_is_deterministic`
    - `tests/unit/dataset/test_folds.py::test_folds_are_chronological`
    - `tests/unit/dataset/test_folds.py::test_shuffling_is_refused`
    - `tests/unit/dataset/test_folds.py::test_the_embargo_is_reported`
    - `tests/unit/dataset/test_folds.py::test_the_test_split_is_locked_until_explicitly_unlocked`
    - `tests/unit/dataset/test_folds.py::test_too_few_rows_for_the_configured_folds_is_refused`
    - `tests/unit/dataset/test_folds.py::test_training_rows_whose_horizon_reaches_validation_are_purged`
    - `tests/unit/dataset/test_join.py::test_a_feature_from_an_unfinalized_bar_is_refused`
    - `tests/unit/dataset/test_join.py::test_a_missing_snapshot_drops_the_row_and_is_counted`
    - `tests/unit/dataset/test_join.py::test_a_snapshot_that_saw_the_future_cannot_be_constructed`
    - `tests/unit/dataset/test_join.py::test_a_tie_on_as_of_is_broken_by_the_later_source_event`
    - `tests/unit/dataset/test_join.py::test_every_drop_reason_is_counted_separately`
    - `tests/unit/dataset/test_join.py::test_only_snapshots_at_or_before_t_are_joined`
    - `tests/unit/dataset/test_join.py::test_the_most_recent_qualifying_snapshot_is_used`
    - `tests/unit/dataset/test_join.py::test_two_indistinguishable_snapshots_are_refused`
    - `tests/unit/dataset/test_labels.py::test_a_label_cannot_claim_to_predate_its_extremum`
    - `tests/unit/dataset/test_labels.py::test_a_labels_availability_is_the_confirmation_time_not_the_extremum`
    - `tests/unit/dataset/test_labels.py::test_a_low_becomes_a_min_label`
    - `tests/unit/dataset/test_labels.py::test_an_extremum_outside_the_window_is_not_counted`
    - `tests/unit/dataset/test_labels.py::test_an_unfinished_horizon_is_not_a_no_turn`
    - `tests/unit/dataset/test_labels.py::test_no_extremum_in_the_horizon_is_a_no_turn`
    - `tests/unit/dataset/test_labels.py::test_rows_with_unfinished_horizons_are_simply_absent`
    - `tests/unit/dataset/test_labels.py::test_the_first_extremum_in_the_window_is_the_label`
    - `tests/unit/dataset/test_leakage.py::test_a_clean_dataset_passes_and_says_what_it_examined`
    - `tests/unit/dataset/test_leakage.py::test_a_feature_from_after_t_is_caught_and_named`
    - `tests/unit/dataset/test_leakage.py::test_a_label_already_knowable_at_t_is_caught`
    - `tests/unit/dataset/test_leakage.py::test_a_label_available_before_its_extremum_is_caught`
    - `tests/unit/dataset/test_leakage.py::test_an_empty_dataset_fails_rather_than_passing_clean`
    - `tests/unit/dataset/test_leakage.py::test_an_unpurged_horizon_is_caught`
    - `tests/unit/dataset/test_leakage.py::test_clean_folds_pass`
    - `tests/unit/dataset/test_leakage.py::test_no_folds_fails_rather_than_passing_clean`
    - `tests/unit/dataset/test_universe.py::test_a_delisted_symbol_is_absent_afterwards`
    - `tests/unit/dataset/test_universe.py::test_a_symbol_listed_later_is_absent_earlier`
    - `tests/unit/dataset/test_universe.py::test_an_empty_universe_drops_everything_visibly`
    - `tests/unit/dataset/test_universe.py::test_eligibility_uses_only_trailing_observations`
    - `tests/unit/dataset/test_universe.py::test_rows_outside_the_universe_are_dropped_and_counted`
- **Code:**
    - `src/channelflow/dataset/__init__.py`
    - `src/channelflow/dataset/certified.py`
    - `src/channelflow/dataset/folds.py`
    - `src/channelflow/dataset/join.py`
    - `src/channelflow/dataset/labels.py`
    - `src/channelflow/dataset/leakage.py`
    - `src/channelflow/dataset/models.py`
- **Outcomes:** [[OUT-2026-09-08-implement-pit-dataset]], [[OUT-2026-09-08-plan-pit-dataset]], [[OUT-2026-09-08-spec-pit-dataset]], [[OUT-2026-09-08-tasks-pit-dataset]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
