---
id: REQ-EXP-007
title: DEX incremental value
type: experiment
prd_ref: "EXP-007 DEX incremental value"
prd_lines: "5117-5126"
phase: null
status: implemented
depends_on: ["REQ-EXP-004", "REQ-WP-015", "REQ-WP-016"]
tags: []
---

## Requirement

For ETH:

- CEX only;
- CEX + DEX price divergence;
- + DEX depth asymmetry;
- + swap imbalance;
- + LP liquidity changes.

## Acceptance

- the five arms appear and are cumulative: CEX only; + DEX price divergence;
  + DEX depth asymmetry; + swap imbalance; + LP liquidity changes;
- an arm whose family contributes no feature is reported as not run, with the
  reason, and never scored;
- every arm is fitted and scored on one fold set;
- the report states the instrument it was run on, because EXP-007 names one
  (ETH).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-040-dex-incremental]]
- **Tests:**
    - `tests/unit/research/test_dex_incremental.py::test_an_arm_naming_a_family_outside_this_taxonomy_is_refused`
    - `tests/unit/research/test_dex_incremental.py::test_one_dex_family_now_resolves_and_three_do_not`
    - `tests/unit/research/test_dex_incremental.py::test_supplied_features_make_the_arms_run`
    - `tests/unit/research/test_dex_incremental.py::test_the_divergence_family_shows_its_increment`
    - `tests/unit/research/test_dex_incremental.py::test_the_five_arms_are_the_prds_and_are_cumulative`
    - `tests/unit/research/test_dex_incremental.py::test_the_instrument_is_required`
    - `tests/unit/research/test_dex_incremental.py::test_the_report_names_the_instrument`
    - `tests/unit/research/test_dex_incremental.py::test_two_runs_produce_equal_reports`
    - `tests/unit/research/test_dex_incremental.py::test_with_the_registry_as_it_is_every_dex_arm_reports_not_run`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/cumulative.py`
    - `src/channelflow/research/dex_incremental.py`
- **Outcomes:** [[OUT-2026-09-09-implement-dex-incremental]], [[OUT-2026-09-09-plan-dex-incremental]], [[OUT-2026-09-09-spec-dex-incremental]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
