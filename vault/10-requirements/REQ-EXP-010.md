---
id: REQ-EXP-010
title: Cross-venue lead/lag
type: experiment
prd_ref: "EXP-010 Cross-venue lead/lag"
prd_lines: "5158-5162"
phase: null
status: implemented
depends_on: ["REQ-WP-016", "REQ-BT-001"]
tags: []
---

## Requirement

Measure whether divergence contains predictive value after realistic latency/costs.

## Acceptance

- predictive value is measured out of sample, never in the window the
  correlation was measured on;
- a latency is applied before any divergence is actionable, and it is a required
  parameter rather than zero by default;
- fees and slippage are applied (PRD §41 rule 9);
- the experiment can conclude `NO_EDGE`, and does so when the out-of-sample
  result does not beat the no-skill baseline after latency and costs;
- no module on the signal path imports this experiment, extending ADR-040's
  import ban to it.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-043-lead-lag-value]]
- **Tests:**
    - `tests/unit/research/test_lead_lag_value.py::test_a_divergence_that_predicts_is_found_out_of_sample`
    - `tests/unit/research/test_lead_lag_value.py::test_a_negative_latency_is_refused`
    - `tests/unit/research/test_lead_lag_value.py::test_a_short_divergence_is_traded_as_a_short`
    - `tests/unit/research/test_lead_lag_value.py::test_latency_can_destroy_the_edge`
    - `tests/unit/research/test_lead_lag_value.py::test_noise_returns_no_edge_and_raises_nothing`
    - `tests/unit/research/test_lead_lag_value.py::test_outcomes_that_are_all_ambiguous_report_rather_than_raise`
    - `tests/unit/research/test_lead_lag_value.py::test_raising_the_costs_lowers_the_out_of_sample_result`
    - `tests/unit/research/test_lead_lag_value.py::test_signals_on_one_side_of_the_split_cannot_be_validated`
    - `tests/unit/research/test_lead_lag_value.py::test_the_costs_refusal_fires_before_anything_is_scored`
    - `tests/unit/research/test_lead_lag_value.py::test_the_first_threshold_that_scores_best_is_kept`
    - `tests/unit/research/test_lead_lag_value.py::test_the_in_sample_score_counts_only_in_sample_signals`
    - `tests/unit/research/test_lead_lag_value.py::test_the_latency_has_no_default`
    - `tests/unit/research/test_lead_lag_value.py::test_the_signal_path_does_not_import_this_study`
    - `tests/unit/research/test_lead_lag_value.py::test_the_study_without_costs_is_refused`
    - `tests/unit/research/test_lead_lag_value.py::test_the_threshold_is_chosen_in_sample_and_scored_out_of_sample`
    - `tests/unit/research/test_lead_lag_value.py::test_two_studies_produce_equal_results`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/lead_lag_value.py`
- **Outcomes:** [[OUT-2026-09-09-implement-lead-lag-value]], [[OUT-2026-09-09-plan-lead-lag-value]], [[OUT-2026-09-09-spec-lead-lag-value]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
