---
id: REQ-EXP-012
title: Causal derivative turning points
type: experiment
prd_ref: "EXP-012 Causal derivative turning points"
prd_lines: "5181-5194"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Compare:

- raw trailing return sign change;
- causal local polynomial order 2;
- causal local polynomial order 3;
- Kalman filtered slope;
- one-sided Savitzky-Golay-equivalent implementation if retained.

Evaluate maximum/minimum forecast precision at horizons 3/6/12/24 bars.

Centered filters are allowed only as retrospective label references, never as live candidates.

## Acceptance

- maximum/minimum forecast precision is evaluated at horizons 3/6/12/24 bars for each candidate method;
- centered filters (e.g. the Savitzky-Golay-equivalent variant) are used only as retrospective label references, never as live candidates.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-045-derivative-turning]]
- **Tests:**
    - `tests/unit/research/test_derivative_turning.py::test_a_call_beyond_the_tolerance_counts_only_at_the_longer_horizons`
    - `tests/unit/research/test_derivative_turning.py::test_a_centred_candidate_is_refused`
    - `tests/unit/research/test_derivative_turning.py::test_a_local_polynomial_reads_the_right_edge_of_its_window`
    - `tests/unit/research/test_derivative_turning.py::test_a_longer_horizon_cannot_lower_precision`
    - `tests/unit/research/test_derivative_turning.py::test_a_smoother_method_calls_fewer_turns_than_the_raw_one`
    - `tests/unit/research/test_derivative_turning.py::test_every_candidate_is_compared`
    - `tests/unit/research/test_derivative_turning.py::test_every_horizon_the_prd_names_is_evaluated`
    - `tests/unit/research/test_derivative_turning.py::test_precision_is_absent_for_a_method_that_calls_nothing`
    - `tests/unit/research/test_derivative_turning.py::test_the_labeller_declares_itself_centred`
    - `tests/unit/research/test_derivative_turning.py::test_the_labels_are_made_by_a_centred_filter_and_the_report_says_so`
    - `tests/unit/research/test_derivative_turning.py::test_the_refusal_comes_from_the_production_guard`
    - `tests/unit/research/test_derivative_turning.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/derivative_turning.py`
- **Outcomes:** [[OUT-2026-09-09-implement-derivative-turning]], [[OUT-2026-09-09-plan-derivative-turning]], [[OUT-2026-09-09-spec-derivative-turning]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
