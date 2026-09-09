---
id: REQ-EXP-004
title: OFI incremental value
type: experiment
prd_ref: "EXP-004 OFI incremental value"
prd_lines: "5092-5101"
phase: null
status: implemented
depends_on: ["REQ-US-006", "REQ-WP-011", "REQ-PRIN-008"]
tags: []
---

## Requirement

Ablation:

- channel only;
- +L1 imbalance;
- +multi-level imbalance;
- +OFI;
- +persistence/cancellation.

## Acceptance

- the five arms appear and are cumulative as the PRD lists them: each contains
  the previous arm's features;
- an arm whose family contributes no feature is reported as not run, with the
  reason, and never scored;
- every arm is fitted and scored on one fold set and one target;
- the report states what each family added over the arm before it, not only each
  arm's absolute score;
- one input produces one report.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-037-ofi-incremental]]
- **Tests:**
    - `tests/unit/research/test_ofi_incremental.py::test_a_family_that_helps_moves_the_increment_the_right_way`
    - `tests/unit/research/test_ofi_incremental.py::test_a_family_with_no_features_is_reported_as_not_run`
    - `tests/unit/research/test_ofi_incremental.py::test_an_arm_naming_a_family_outside_this_taxonomy_is_refused`
    - `tests/unit/research/test_ofi_incremental.py::test_an_increment_over_an_unscored_arm_is_absent_not_zero`
    - `tests/unit/research/test_ofi_incremental.py::test_each_increment_names_what_it_added`
    - `tests/unit/research/test_ofi_incremental.py::test_every_arm_appears_in_the_report`
    - `tests/unit/research/test_ofi_incremental.py::test_every_arm_is_scored_on_the_same_folds`
    - `tests/unit/research/test_ofi_incremental.py::test_the_families_are_resolved_from_the_registry`
    - `tests/unit/research/test_ofi_incremental.py::test_the_families_resolve_in_a_process_that_imported_nothing_else`
    - `tests/unit/research/test_ofi_incremental.py::test_the_five_arms_are_the_prds_and_are_cumulative`
    - `tests/unit/research/test_ofi_incremental.py::test_the_us_006_taxonomy_still_refuses_this_ones_families`
    - `tests/unit/research/test_ofi_incremental.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/channels/features.py`
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/cumulative.py`
    - `src/channelflow/research/ofi_incremental.py`
- **Outcomes:** [[OUT-2026-09-09-implement-ofi-incremental]], [[OUT-2026-09-09-plan-ofi-incremental]], [[OUT-2026-09-09-spec-ofi-incremental]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
