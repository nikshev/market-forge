---
id: REQ-EXP-003
title: Rejection detector
type: experiment
prd_ref: "EXP-003 Rejection detector"
prd_lines: "5083-5091"
phase: null
status: implemented
depends_on: ["REQ-WP-007", "REQ-BT-001", "REQ-EXP-001"]
tags: []
---

## Requirement

Compare:

- wick only;
- close-back-inside;
- two-bar confirmation;
- order-flow confirmation.

## Acceptance

- all four detectors — wick only, close-back-inside, two-bar confirmation,
  order-flow confirmation — appear in the report;
- each detector used is a production `RejectionDetector` driven by the signal
  machine, never a copy of its logic (PRD §25.2);
- a detector whose inputs do not exist is reported as unavailable with the
  reason, and is not scored;
- for each detector, over identical bars and one split: confirmation count,
  median confirmation lag in bars, the share of confirmations later invalidated,
  and expectancy in R after costs out of sample;
- the ranking is by a declared rule, and the report states that a detector may
  win on lag and lose on expectancy;
- one input produces one report.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-036-detector-comparison]]
- **Tests:**
    - `tests/unit/research/test_detector_comparison.py::test_a_bodyless_bar_with_a_wick_is_a_rejection_not_a_division_by_zero`
    - `tests/unit/research/test_detector_comparison.py::test_a_confirmation_the_market_takes_back_is_counted`
    - `tests/unit/research/test_detector_comparison.py::test_a_detector_that_confirms_nothing_is_reported_with_its_reason`
    - `tests/unit/research/test_detector_comparison.py::test_a_permissive_detector_confirms_sooner_than_a_strict_one`
    - `tests/unit/research/test_detector_comparison.py::test_all_four_detectors_appear_in_the_report`
    - `tests/unit/research/test_detector_comparison.py::test_an_invalidation_before_confirmation_is_not_counted_as_taken_back`
    - `tests/unit/research/test_detector_comparison.py::test_each_detector_runs_inside_the_production_machine`
    - `tests/unit/research/test_detector_comparison.py::test_expectancy_counts_only_out_of_sample_confirmations`
    - `tests/unit/research/test_detector_comparison.py::test_the_close_back_inside_detector_is_the_one_the_engine_ships_with`
    - `tests/unit/research/test_detector_comparison.py::test_the_comparison_without_costs_is_refused`
    - `tests/unit/research/test_detector_comparison.py::test_the_four_metrics_are_reported_for_a_detector_that_traded`
    - `tests/unit/research/test_detector_comparison.py::test_the_lag_is_the_distance_from_opening_to_confirmation`
    - `tests/unit/research/test_detector_comparison.py::test_the_ranking_is_by_expectancy_and_excludes_the_unscored`
    - `tests/unit/research/test_detector_comparison.py::test_the_taken_back_share_reaches_the_report`
    - `tests/unit/research/test_detector_comparison.py::test_the_two_bar_detector_cannot_answer_on_its_first_bar`
    - `tests/unit/research/test_detector_comparison.py::test_the_two_bar_detector_refuses_a_higher_close`
    - `tests/unit/research/test_detector_comparison.py::test_the_unavailable_detector_is_named_and_never_scored`
    - `tests/unit/research/test_detector_comparison.py::test_the_wick_detector_reads_the_bar_the_prd_describes`
    - `tests/unit/research/test_detector_comparison.py::test_the_wick_detector_reads_the_lower_wick_for_a_long`
    - `tests/unit/research/test_detector_comparison.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/detector_comparison.py`
    - `src/channelflow/signals/__init__.py`
    - `src/channelflow/signals/rejection.py`
- **Outcomes:** [[OUT-2026-09-09-implement-detector-comparison]], [[OUT-2026-09-09-plan-detector-comparison]], [[OUT-2026-09-09-spec-detector-comparison]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
