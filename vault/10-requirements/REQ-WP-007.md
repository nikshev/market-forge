---
id: REQ-WP-007
title: Signal state machine
type: work-package
prd_ref: "WP-007 Signal state machine"
prd_lines: "6983-6986"
phase: null
status: implemented
depends_on: ["REQ-WP-006"]
tags: []
---

## Requirement

Implement long/short boundary + middle setups with deterministic transitions and tests.

## Acceptance

- long/short boundary and middle setups are implemented;
- state transitions are deterministic;
- transitions are covered by tests.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-008-signal-state-machine]]
- **Tests:**
    - `tests/unit/signals/test_lifecycle.py::test_a_long_setup_opens_at_the_lower_boundary`
    - `tests/unit/signals/test_lifecycle.py::test_an_illegal_move_is_refused_rather_than_performed`
    - `tests/unit/signals/test_lifecycle.py::test_approach_touch_reject_confirm_is_the_path`
    - `tests/unit/signals/test_lifecycle.py::test_no_transition_skips_a_step`
    - `tests/unit/signals/test_lifecycle.py::test_price_outside_every_zone_opens_nothing`
    - `tests/unit/signals/test_lifecycle.py::test_the_same_bars_twice_give_identical_paths_and_records`
    - `tests/unit/signals/test_preconditions.py::test_a_channel_whose_slope_opposes_the_direction_opens_nothing`
    - `tests/unit/signals/test_preconditions.py::test_a_close_beyond_the_outer_tolerance_invalidates`
    - `tests/unit/signals/test_preconditions.py::test_a_low_quality_channel_opens_nothing`
    - `tests/unit/signals/test_preconditions.py::test_no_channel_means_nothing_opens_and_nothing_advances`
    - `tests/unit/signals/test_preconditions.py::test_quality_collapse_invalidates_with_a_recorded_reason`
    - `tests/unit/signals/test_preconditions.py::test_the_same_price_action_opens_under_a_supporting_channel`
    - `tests/unit/signals/test_termination.py::test_a_candidate_expires_after_the_configured_bars`
    - `tests/unit/signals/test_termination.py::test_a_confirmed_candidate_does_not_expire`
    - `tests/unit/signals/test_termination.py::test_a_second_detector_registers_without_touching_the_machine`
    - `tests/unit/signals/test_termination.py::test_an_expired_candidate_does_not_revive`
- **Code:**
    - `src/channelflow/signals/__init__.py`
    - `src/channelflow/signals/machine.py`
    - `src/channelflow/signals/models.py`
    - `src/channelflow/signals/rejection.py`
- **Outcomes:** [[OUT-2026-09-08-implement-signal-state-machine]], [[OUT-2026-09-08-plan-signal-state-machine]], [[OUT-2026-09-08-spec-signal-state-machine]], [[OUT-2026-09-08-tasks-signal-state-machine]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
