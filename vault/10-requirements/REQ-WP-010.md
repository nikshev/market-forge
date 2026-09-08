---
id: REQ-WP-010
title: Backtest v1
type: work-package
prd_ref: "WP-010 Backtest v1"
prd_lines: "7004-7010"
phase: null
status: implemented
depends_on: ["REQ-WP-005", "REQ-WP-006", "REQ-WP-007"]
tags: []
---

## Requirement

- virtual clock;
- bar replay;
- strategy reuse;
- reports.

## Acceptance

- backtest runs on a virtual clock;
- backtest replays bars;
- backtest reuses the live strategy/signal engine rather than a separate implementation;
- backtest produces reports.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-009-backtest-v1]]
- **Tests:**
    - `tests/unit/backtest/test_parity.py::test_parity_covers_a_full_lifecycle_not_just_openings`
    - `tests/unit/backtest/test_parity.py::test_replay_matches_the_live_engine_transition_for_transition`
    - `tests/unit/backtest/test_report.py::test_an_empty_run_reports_zeroes_rather_than_dividing_by_them`
    - `tests/unit/backtest/test_report.py::test_bars_without_enough_history_are_reported_as_skipped`
    - `tests/unit/backtest/test_report.py::test_candidates_are_counted_by_direction_and_boundary`
    - `tests/unit/backtest/test_report.py::test_the_confirmation_rate_and_terminal_reasons_are_reported`
    - `tests/unit/backtest/test_report.py::test_the_report_cannot_be_edited_after_the_fact`
    - `tests/unit/backtest/test_report.py::test_the_report_carries_no_economic_metric`
    - `tests/unit/backtest/test_report.py::test_the_report_covers_the_bars_event_time_range`
    - `tests/unit/backtest/test_report.py::test_two_configurations_give_different_reports_and_each_names_its_own`
    - `tests/unit/backtest/test_virtual_clock.py::test_a_run_does_not_disturb_the_machine_it_was_given`
    - `tests/unit/backtest/test_virtual_clock.py::test_bars_are_replayed_in_event_time_order`
    - `tests/unit/backtest/test_virtual_clock.py::test_the_backtest_cannot_consult_a_clock`
    - `tests/unit/backtest/test_virtual_clock.py::test_the_runner_never_shows_the_channel_a_future_bar`
    - `tests/unit/backtest/test_virtual_clock.py::test_two_runs_over_the_same_bars_are_identical`
    - `tests/unit/backtest/test_virtual_clock.py::test_unfinalized_bars_are_not_replayed`
- **Code:**
    - `src/channelflow/backtest/__init__.py`
    - `src/channelflow/backtest/report.py`
    - `src/channelflow/backtest/runner.py`
- **Outcomes:** [[OUT-2026-09-08-implement-backtest-v1]], [[OUT-2026-09-08-plan-backtest-v1]], [[OUT-2026-09-08-spec-backtest-v1]], [[OUT-2026-09-08-tasks-backtest-v1]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
