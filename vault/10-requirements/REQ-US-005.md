---
id: REQ-US-005
title: Backtest a setup family
type: user-story
prd_ref: "US-005 — Backtest a setup family"
prd_lines: "267-270"
phase: null
status: implemented
depends_on: ["REQ-WP-007", "REQ-WP-010"]
tags: []
---

## Requirement

As a researcher, I want to backtest `upper_rejection_short` separately from `middle_continuation_short`.

## Acceptance

- `upper_rejection_short` and `middle_continuation_short` can each be backtested independently, as separate setup families.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-029-setup-families]]
- **Tests:**
    - `tests/unit/backtest/test_families.py::test_a_family_less_run_is_unchanged`
    - `tests/unit/backtest/test_families.py::test_a_family_restricts_direction_as_well_as_zone`
    - `tests/unit/backtest/test_families.py::test_a_family_run_opens_only_its_own_candidates`
    - `tests/unit/backtest/test_families.py::test_an_impossible_zone_is_refused[zone0]`
    - `tests/unit/backtest/test_families.py::test_an_impossible_zone_is_refused[zone1]`
    - `tests/unit/backtest/test_families.py::test_an_impossible_zone_is_refused[zone2]`
    - `tests/unit/backtest/test_families.py::test_neither_familys_count_depends_on_the_others_setups`
    - `tests/unit/backtest/test_families.py::test_the_family_adds_no_strategy_logic`
    - `tests/unit/backtest/test_families.py::test_the_familys_thresholds_are_in_its_report`
    - `tests/unit/backtest/test_families.py::test_the_familys_zone_is_what_the_machine_uses`
    - `tests/unit/backtest/test_families.py::test_the_other_family_runs_on_the_same_bars_and_sees_its_own`
    - `tests/unit/backtest/test_families.py::test_the_report_names_the_family`
    - `tests/unit/backtest/test_families.py::test_the_two_families_differ_in_configuration_not_in_code`
    - `tests/unit/backtest/test_families.py::test_upper_rejection_short_carries_the_prds_own_numbers`
- **Code:**
    - `src/channelflow/backtest/__init__.py`
    - `src/channelflow/backtest/families.py`
    - `src/channelflow/backtest/report.py`
    - `src/channelflow/backtest/runner.py`
- **Outcomes:** [[OUT-2026-09-09-implement-setup-families]], [[OUT-2026-09-09-plan-setup-families]], [[OUT-2026-09-09-spec-setup-families]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
