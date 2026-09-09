---
id: REQ-EXP-014
title: Order-flow exhaustion around extrema
type: experiment
prd_ref: "EXP-014 Order-flow exhaustion around extrema"
prd_lines: "5216-5228"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Conditional study around future-labeled meaningful extrema:

- OFI sign and slope;
- CVD divergence;
- microprice deviation;
- spread widening;
- wall replenishment/cancellation;
- absorption.

Then repeat point-in-time as a predictive experiment to avoid confusing contemporaneous explanation with forecast value.

## Acceptance

- the conditional study is repeated in a point-in-time (predictive) form, separate from the contemporaneous conditional study, so that explanatory value around extrema is not confused with forecast value.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-047-order-flow-exhaustion]]
- **Tests:**
    - `tests/unit/research/test_exhaustion.py::test_a_missing_signal_is_refused`
    - `tests/unit/research/test_exhaustion.py::test_a_series_too_short_to_decide_anything_is_refused`
    - `tests/unit/research/test_exhaustion.py::test_a_signal_related_to_nothing_is_named_as_such`
    - `tests/unit/research/test_exhaustion.py::test_a_signal_that_does_both_is_named_as_such`
    - `tests/unit/research/test_exhaustion.py::test_a_signal_that_explains_but_does_not_forecast_is_named_as_such`
    - `tests/unit/research/test_exhaustion.py::test_a_signal_that_never_stands_out_has_no_precision`
    - `tests/unit/research/test_exhaustion.py::test_an_extremum_outside_the_series_is_refused`
    - `tests/unit/research/test_exhaustion.py::test_both_studies_are_reported_for_every_signal`
    - `tests/unit/research/test_exhaustion.py::test_control_bars_are_kept_away_from_every_turn`
    - `tests/unit/research/test_exhaustion.py::test_every_bullet_the_prd_names_is_studied`
    - `tests/unit/research/test_exhaustion.py::test_the_calling_threshold_reads_no_bar_at_or_after_the_decision`
    - `tests/unit/research/test_exhaustion.py::test_the_conditional_arm_declares_itself_retrospective`
    - `tests/unit/research/test_exhaustion.py::test_the_horizon_includes_its_own_last_bar`
    - `tests/unit/research/test_exhaustion.py::test_the_predictive_arm_decides_only_bars_with_a_full_horizon_ahead`
    - `tests/unit/research/test_exhaustion.py::test_the_research_judgements_are_required_and_bounded`
    - `tests/unit/research/test_exhaustion.py::test_the_two_arms_disagree_on_the_same_series`
    - `tests/unit/research/test_exhaustion.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/exhaustion.py`
- **Outcomes:** [[OUT-2026-09-09-implement-order-flow-exhaustion]], [[OUT-2026-09-09-plan-order-flow-exhaustion]], [[OUT-2026-09-09-spec-order-flow-exhaustion]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
