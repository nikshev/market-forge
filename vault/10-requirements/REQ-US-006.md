---
id: REQ-US-006
title: Compare feature families
type: user-story
prd_ref: "US-006 — Compare feature families"
prd_lines: "271-280"
phase: null
status: implemented
depends_on: ["REQ-WP-017", "REQ-WP-018", "REQ-WP-019"]
tags: []
---

## Requirement

As a researcher, I want to run an ablation:

- channel only;
- channel + order flow;
- channel + derivatives;
- channel + DEX;
- all combined.

## Acceptance

- an ablation report exists comparing: channel only; channel + order flow; channel + derivatives; channel + DEX; all combined.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-030-ablation]]
- **Tests:**
    - `tests/unit/research/test_ablation.py::test_a_feature_in_two_families_is_counted_once`
    - `tests/unit/research/test_ablation.py::test_a_report_with_nothing_runnable_says_so`
    - `tests/unit/research/test_ablation.py::test_adding_a_family_can_only_add_features`
    - `tests/unit/research/test_ablation.py::test_all_combined_contains_every_other_arms_families`
    - `tests/unit/research/test_ablation.py::test_all_five_arms_appear_in_the_report`
    - `tests/unit/research/test_ablation.py::test_an_arm_identical_to_an_earlier_one_names_it`
    - `tests/unit/research/test_ablation.py::test_an_arm_with_no_features_for_its_families_is_not_run`
    - `tests/unit/research/test_ablation.py::test_an_unknown_family_is_refused`
    - `tests/unit/research/test_ablation.py::test_an_unrun_arm_is_not_ranked`
    - `tests/unit/research/test_ablation.py::test_every_scored_arm_ran_on_the_same_folds`
    - `tests/unit/research/test_ablation.py::test_the_ranking_breaks_ties_by_name`
    - `tests/unit/research/test_ablation.py::test_the_research_package_consults_no_clock_or_random_source`
    - `tests/unit/research/test_ablation.py::test_two_arms_that_score_identically_rank_by_name`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/ablation.py`
- **Outcomes:** [[OUT-2026-09-09-implement-ablation]], [[OUT-2026-09-09-plan-ablation]], [[OUT-2026-09-09-spec-ablation]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
