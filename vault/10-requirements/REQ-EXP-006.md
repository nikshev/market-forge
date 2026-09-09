---
id: REQ-EXP-006
title: Derivatives context
type: experiment
prd_ref: "EXP-006 Derivatives context"
prd_lines: "5108-5116"
phase: null
status: implemented
depends_on: ["REQ-WP-013", "REQ-BT-001"]
tags: []
---

## Requirement

Analyze conditional outcomes by:

- funding z-score;
- OI change;
- liquidation imbalance;
- basis.

## Acceptance

- outcomes are reported conditionally on each of the four variables: funding
  z-score, OI change, liquidation imbalance, basis;
- each variable is bucketed by a declared rule, and every bucket is reported
  with its count;
- a variable with no data is reported as unavailable, not as a flat conditional;
- every conditional is computed over the same outcomes and the same costs;
- a contemporaneous conditional is labelled as such, so explanatory value around
  an outcome is not read as forecast value (EXP-014's own warning).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-039-derivatives-context]]
- **Tests:**
    - `tests/unit/research/test_derivatives_context.py::test_a_bucket_too_small_is_reported_and_not_scored`
    - `tests/unit/research/test_derivatives_context.py::test_a_contemporaneous_study_says_so`
    - `tests/unit/research/test_derivatives_context.py::test_a_variable_with_no_data_is_unavailable_not_a_flat_conditional`
    - `tests/unit/research/test_derivatives_context.py::test_all_four_variables_are_reported`
    - `tests/unit/research/test_derivatives_context.py::test_ambiguous_outcomes_are_excluded_and_counted`
    - `tests/unit/research/test_derivatives_context.py::test_every_conditional_uses_the_same_costs`
    - `tests/unit/research/test_derivatives_context.py::test_raising_the_costs_lowers_every_bucket`
    - `tests/unit/research/test_derivatives_context.py::test_the_buckets_are_the_declared_edges_and_carry_their_counts`
    - `tests/unit/research/test_derivatives_context.py::test_the_conditional_separates_the_buckets_it_should`
    - `tests/unit/research/test_derivatives_context.py::test_the_point_in_time_flag_has_no_default`
    - `tests/unit/research/test_derivatives_context.py::test_the_study_without_costs_is_refused`
    - `tests/unit/research/test_derivatives_context.py::test_two_studies_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/derivatives_context.py`
- **Outcomes:** [[OUT-2026-09-09-implement-derivatives-context]], [[OUT-2026-09-09-plan-derivatives-context]], [[OUT-2026-09-09-spec-derivatives-context]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
