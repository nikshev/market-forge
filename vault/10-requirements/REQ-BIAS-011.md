---
id: REQ-BIAS-011
title: Store all discarded experiment variants to reduce silent cherry-picking.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5327-5327"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Store all discarded experiment variants to reduce silent cherry-picking.

## Acceptance

Store all discarded experiment variants to reduce silent cherry-picking.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-053-experiment-registry]], [[SPEC-057-experiment-gate-adoption]]
- **Tests:**
    - `tests/unit/experiments/test_fields.py::test_a_callable_nested_inside_a_config_is_stabilised_too`
    - `tests/unit/experiments/test_fields.py::test_a_chosen_variant_goes_through_the_gate`
    - `tests/unit/experiments/test_fields.py::test_a_comparison_that_chose_nothing_records_and_reports_nothing`
    - `tests/unit/experiments/test_fields.py::test_a_config_names_the_class_it_came_from`
    - `tests/unit/experiments/test_fields.py::test_a_field_may_choose_nothing`
    - `tests/unit/experiments/test_fields.py::test_a_field_of_nothing_is_refused`
    - `tests/unit/experiments/test_fields.py::test_a_field_whose_config_cannot_be_hashed_is_refused`
    - `tests/unit/experiments/test_fields.py::test_a_variant_holding_a_closure_hashes_the_same_on_the_next_run`
    - `tests/unit/experiments/test_fields.py::test_a_variant_that_exposes_nothing_is_identified_by_its_type_alone`
    - `tests/unit/experiments/test_fields.py::test_a_variant_that_is_not_a_dataclass_reports_what_it_exposes`
    - `tests/unit/experiments/test_fields.py::test_a_winner_missing_from_the_registry_is_still_refused`
    - `tests/unit/experiments/test_fields.py::test_a_winner_outside_its_own_field_cannot_be_constructed`
    - `tests/unit/experiments/test_fields.py::test_an_unreproducible_run_is_recorded_and_refused`
    - `tests/unit/experiments/test_fields.py::test_enum_variants_do_not_all_share_one_config`
    - `tests/unit/experiments/test_fields.py::test_every_field_of_a_variant_survives_into_its_config`
    - `tests/unit/experiments/test_fields.py::test_every_variant_reaches_the_registry`
    - `tests/unit/experiments/test_fields.py::test_reporting_one_field_twice_does_not_double_it`
    - `tests/unit/experiments/test_fields.py::test_the_chosen_variant_is_the_only_one_kept`
    - `tests/unit/experiments/test_fields.py::test_the_class_of_a_variant_is_refused_as_a_variant`
    - `tests/unit/experiments/test_fields.py::test_two_functions_of_one_name_in_different_modules_do_not_collide`
    - `tests/unit/experiments/test_fields.py::test_two_variants_of_one_class_do_not_share_a_config`
    - `tests/unit/experiments/test_fields.py::test_variants_that_differed_get_different_identities`
    - `tests/unit/experiments/test_registry.py::test_a_discarded_variant_is_recorded_exactly_like_a_kept_one`
    - `tests/unit/experiments/test_registry.py::test_the_registry_is_append_only_and_its_history_does_not_change`
    - `tests/unit/experiments/test_report.py::test_a_field_of_one_is_a_legitimate_report`
    - `tests/unit/experiments/test_report.py::test_a_field_that_counts_a_variant_twice_is_refused`
    - `tests/unit/experiments/test_report.py::test_a_variant_that_lost_and_was_never_recorded_stops_the_report`
    - `tests/unit/experiments/test_report.py::test_a_winner_that_is_not_in_its_own_field_is_refused`
    - `tests/unit/research/test_gate_adoption.py::test_a_field_type_is_what_the_seam_expects`
    - `tests/unit/research/test_gate_adoption.py::test_a_real_comparison_reaches_the_registry`
    - `tests/unit/research/test_gate_adoption.py::test_an_experiment_id_is_not_empty`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[ablation]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[channel_comparison]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[corridor_calibration]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[cumulative]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[defi_confluence]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[derivative_turning]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[derivatives_context]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[detector_comparison]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[dex_incremental]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[exhaustion]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[extremum_detectors]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[gmdh_extrema]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[lead_lag_value]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[lookback_sensitivity]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[multi_scale]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[ofi_incremental]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[stop_policies]`
    - `tests/unit/research/test_gate_adoption.py::test_every_comparison_can_name_its_field[volume_confluence]`
    - `tests/unit/research/test_gate_adoption.py::test_every_research_module_declares_its_experiment_and_comparison`
    - `tests/unit/research/test_gate_adoption.py::test_no_two_modules_claim_the_same_experiment`
    - `tests/unit/research/test_lead_lag_value.py::test_a_study_that_could_not_choose_still_names_the_field_it_tried`
    - `tests/unit/research/test_lead_lag_value.py::test_every_threshold_swept_is_in_the_field`
- **Code:**
    - `src/channelflow/experiments/__init__.py`
    - `src/channelflow/experiments/fields.py`
    - `src/channelflow/experiments/registry.py`
    - `src/channelflow/experiments/report.py`
    - `src/channelflow/research/__init__.py`
- **Outcomes:** [[OUT-2026-09-09-implement-experiment-registry]], [[OUT-2026-09-09-plan-experiment-registry]], [[OUT-2026-09-09-requirement-experiment-registry]], [[OUT-2026-09-09-spec-experiment-registry]], [[OUT-2026-09-10-implement-experiment-gate-adoption]], [[OUT-2026-09-10-plan-experiment-gate-adoption]], [[OUT-2026-09-10-spec-experiment-gate-adoption]]
<!-- trace:end -->

## Notes

[[ADR-024]] recorded that this rule had no home: "experiment tracking, which
nothing here does". [[REQ-REPRO-001]] builds one — a registry on the canonical
plane that records every variant, kept or discarded, and a reporting gate that
refuses a winner whose field is not on record.

The status stood at `specified` until 2026-09-10, deliberately: the mechanism
existed and nothing published through it, and marking the rule implemented on
the strength of an unused gate would have claimed the coverage [[ADR-024]]
refused to claim for rule 2 on the strength of one engine's guard. See
[[ADR-054]].

The experiments have adopted it. All eighteen research modules declare their
experiment and their comparison, and every comparison can be asked what it
compared — checked by walking the package rather than by a list, so a
nineteenth joins the rule instead of quietly escaping it
([[SPEC-057-experiment-gate-adoption]]).

What the rule still cannot do is unchanged and worth keeping in view: the gate
stops a variant that was run, lost and quietly dropped. It cannot stop someone
who never mentions a variant at all, and it does not reach a person who reads a
report object and quotes one line of it in a document.

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
