---
id: REQ-EXP-005
title: Volume profile confluence
type: experiment
prd_ref: "EXP-005 Volume profile confluence"
prd_lines: "5102-5107"
phase: null
status: implemented
depends_on: ["REQ-WP-012", "REQ-BT-001"]
tags: []
---

## Requirement

Question:

Does boundary overlap with VAH/VAL/HVN/LVN materially change target-before-stop probability?

## Acceptance

- the two populations are defined point-in-time: setups whose boundary overlaps
  a VAH, VAL, HVN or LVN level at signal time, and those whose boundary does
  not;
- target-before-stop probability is computed for each from REQ-BT-001's
  outcomes, with ambiguous outcomes excluded and counted;
- "materially" is a configured effect size, declared before the comparison and
  reported with the result;
- the answer is one of three — higher, lower, or not materially different — and
  the third is a result rather than a failure;
- a population too small to support the comparison refuses rather than reporting
  a difference.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-038-volume-confluence]]
- **Tests:**
    - `tests/unit/research/test_volume_confluence.py::test_a_boundary_at_the_value_area_edge_is_confluent`
    - `tests/unit/research/test_volume_confluence.py::test_a_boundary_away_from_every_level_is_not_confluent`
    - `tests/unit/research/test_volume_confluence.py::test_a_boundary_on_a_high_volume_node_is_confluent`
    - `tests/unit/research/test_volume_confluence.py::test_a_higher_probability_with_confluence_is_reported_as_higher`
    - `tests/unit/research/test_volume_confluence.py::test_a_lower_probability_with_confluence_is_reported_as_lower`
    - `tests/unit/research/test_volume_confluence.py::test_a_negative_effect_size_is_refused`
    - `tests/unit/research/test_volume_confluence.py::test_a_population_that_decided_nothing_refuses`
    - `tests/unit/research/test_volume_confluence.py::test_a_population_too_small_refuses`
    - `tests/unit/research/test_volume_confluence.py::test_a_small_difference_is_not_materially_different`
    - `tests/unit/research/test_volume_confluence.py::test_ambiguous_outcomes_are_excluded_and_counted`
    - `tests/unit/research/test_volume_confluence.py::test_the_band_decides_how_close_counts`
    - `tests/unit/research/test_volume_confluence.py::test_the_effect_size_is_the_callers_and_has_no_default`
    - `tests/unit/research/test_volume_confluence.py::test_the_same_difference_flips_the_verdict_when_the_effect_size_changes`
    - `tests/unit/research/test_volume_confluence.py::test_timeouts_are_counted_but_are_not_decisions`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/volume_confluence.py`
- **Outcomes:** [[OUT-2026-09-09-implement-volume-confluence]], [[OUT-2026-09-09-plan-volume-confluence]], [[OUT-2026-09-09-spec-volume-confluence]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
