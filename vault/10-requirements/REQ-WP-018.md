---
id: REQ-WP-018
title: GMDH
type: work-package
prd_ref: "WP-018 GMDH"
prd_lines: "7062-7071"
phase: null
status: implemented
depends_on: ["REQ-WP-017"]
tags: []
---

## Requirement

- model abstraction;
- polynomial node search;
- complexity constraints;
- validation criterion;
- feature interaction export;
- comparison report.

## Acceptance

- a model abstraction exists;
- polynomial node search is implemented;
- complexity constraints are enforced;
- a validation criterion selects/prunes candidates;
- feature interactions can be exported;
- a comparison report against baselines exists (per REQ-PRIN-006).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-018-gmdh]]
- **Tests:**
    - `tests/unit/models/test_gmdh.py::test_a_constant_target_is_refused`
    - `tests/unit/models/test_gmdh.py::test_a_search_names_why_it_stopped`
    - `tests/unit/models/test_gmdh.py::test_a_single_row_scoring_split_is_refused`
    - `tests/unit/models/test_gmdh.py::test_interactions_resolve_to_original_input_names`
    - `tests/unit/models/test_gmdh.py::test_overlapping_splits_are_refused`
    - `tests/unit/models/test_gmdh.py::test_selection_uses_data_the_node_was_not_fitted_on`
    - `tests/unit/models/test_gmdh.py::test_the_layer_budget_is_respected`
    - `tests/unit/models/test_gmdh.py::test_the_models_package_cannot_consult_a_clock`
    - `tests/unit/models/test_gmdh.py::test_the_protocol_fit_refuses_rather_than_inventing_a_split`
    - `tests/unit/models/test_gmdh.py::test_the_search_stops_when_a_layer_stops_improving`
    - `tests/unit/models/test_gmdh.py::test_the_width_budget_is_respected`
    - `tests/unit/models/test_gmdh.py::test_too_few_inputs_is_refused`
    - `tests/unit/models/test_gmdh.py::test_training_is_deterministic`
    - `tests/unit/models/test_report.py::test_a_model_that_does_not_beat_the_base_rate_is_reported_as_such`
    - `tests/unit/models/test_report.py::test_a_tie_with_the_base_rate_does_not_count_as_beating_it`
    - `tests/unit/models/test_report.py::test_brier_rewards_calibration_not_confidence`
    - `tests/unit/models/test_report.py::test_every_baseline_from_the_prd_appears_in_the_report`
    - `tests/unit/models/test_report.py::test_gmdh_beats_the_linear_baseline_on_an_interaction_target`
    - `tests/unit/models/test_report.py::test_the_report_refuses_overlapping_splits`
    - `tests/unit/models/test_report.py::test_the_report_scores_the_model_and_baselines_on_identical_data`
    - `tests/unit/models/test_report.py::test_unrun_baselines_carry_their_reason`
- **Code:**
    - `src/channelflow/models/__init__.py`
    - `src/channelflow/models/base.py`
    - `src/channelflow/models/boosting.py`
    - `src/channelflow/models/gmdh.py`
    - `src/channelflow/models/regularized.py`
    - `src/channelflow/models/report.py`
- **Outcomes:** [[OUT-2026-09-08-implement-gmdh]], [[OUT-2026-09-08-spec-gmdh]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
