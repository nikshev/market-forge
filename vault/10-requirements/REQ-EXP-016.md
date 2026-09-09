---
id: REQ-EXP-016
title: Multi-scale extrema
type: experiment
prd_ref: "EXP-016 Multi-scale extrema"
prd_lines: "5241-5251"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Evaluate whether nested extrema improve signals:

- 5m candidate inside 15m upper/lower zone;
- 15m candidate aligned/conflicted with 1h slope;
- directional-change thresholds at multiple scales.

Measure incremental value, not visual appeal.

## Acceptance

- incremental value of nested/multi-scale extrema (5m-inside-15m zone, 15m-vs-1h slope alignment, multi-scale directional-change thresholds) is measured quantitatively, not judged by visual appeal.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-049-multi-scale-extrema]]
- **Tests:**
    - `tests/unit/research/test_multi_scale.py::test_a_candidate_without_context_is_excluded_from_every_arm`
    - `tests/unit/research/test_multi_scale.py::test_a_direction_that_is_neither_long_nor_short_is_refused`
    - `tests/unit/research/test_multi_scale.py::test_a_rule_outside_the_three_is_refused`
    - `tests/unit/research/test_multi_scale.py::test_a_rule_that_earns_its_selectivity_is_named_as_such`
    - `tests/unit/research/test_multi_scale.py::test_a_rule_that_helps_neither_way_is_named_as_such`
    - `tests/unit/research/test_multi_scale.py::test_a_rule_that_keeps_nothing_has_no_expectancy`
    - `tests/unit/research/test_multi_scale.py::test_a_rule_that_looks_better_than_it_is_is_named_as_such`
    - `tests/unit/research/test_multi_scale.py::test_every_rule_reports_the_average_trade_and_the_total`
    - `tests/unit/research/test_multi_scale.py::test_frames_out_of_closing_order_are_refused`
    - `tests/unit/research/test_multi_scale.py::test_multiple_scales_means_both_of_them`
    - `tests/unit/research/test_multi_scale.py::test_only_a_closed_higher_frame_is_visible`
    - `tests/unit/research/test_multi_scale.py::test_the_improvement_floor_decides_what_counts_as_an_improvement`
    - `tests/unit/research/test_multi_scale.py::test_the_improvement_floor_is_required_and_positive`
    - `tests/unit/research/test_multi_scale.py::test_the_rejected_candidates_are_reported_too`
    - `tests/unit/research/test_multi_scale.py::test_the_three_rules_the_prd_names_are_evaluated`
    - `tests/unit/research/test_multi_scale.py::test_the_zone_includes_its_own_edges`
    - `tests/unit/research/test_multi_scale.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/multi_scale.py`
- **Outcomes:** [[OUT-2026-09-09-implement-multi-scale-extrema]], [[OUT-2026-09-09-plan-multi-scale-extrema]], [[OUT-2026-09-09-spec-multi-scale-extrema]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
