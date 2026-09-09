---
id: REQ-WP-020
title: Adaptive stop management
type: work-package
prd_ref: "WP-020 Adaptive stop management"
prd_lines: "7100-7136"
phase: null
status: implemented
depends_on: ["REQ-WP-006", "REQ-WP-011", "REQ-WP-013", "REQ-WP-019"]
tags: []
---

## Requirement

Implement in this order:

1. `PositionState`, `StopAnchor`, `StopProposal`, `StopPolicyOutcome` models;
2. manual/shadow position ingestion;
3. initial structural stop + causal volatility/noise buffer;
4. deterministic position-phase state machine;
5. confirmed-swing trailing baseline;
6. monotonic tightening guard;
7. minimum-distance guard;
8. hysteresis/cooldown/anti-churn;
9. channel-aware anchors;
10. order-flow confirmation/veto;
11. turning-point transition into defensive mode;
12. derivatives/DeFi context adapters;
13. data-quality freeze;
14. counterfactual stop-policy replay;
15. naive fixed-percent and ATR trailing baselines;
16. UI stop path + reason inspector;
17. Telegram stop-update event;
18. optional exchange reconciliation interface behind disabled feature flag.

Done when:

- no-future-swing legality test passes;
- LONG/SHORT monotonic tightening tests pass;
- stop-path replay is deterministic;
- adaptive vs naive OOS report exists;
- premature-stop metric exists;
- stop update latency is represented in replay;
- module is usable in shadow/paper mode without any exchange trading key;
- ML is not required for baseline completion.


---

## Acceptance

- no-future-swing legality test passes;
- LONG/SHORT monotonic tightening tests pass;
- stop-path replay is deterministic;
- adaptive vs naive OOS report exists;
- premature-stop metric exists;
- stop update latency is represented in replay;
- module is usable in shadow/paper mode without any exchange trading key;
- ML is not required for baseline completion.


---

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-019-adaptive-stops]]
- **Tests:**
    - `tests/unit/stops/test_policy.py::test_a_buffer_may_not_loosen_the_stop_even_inside_the_initial_risk`
    - `tests/unit/stops/test_policy.py::test_a_cooldown_holds_the_next_movement`
    - `tests/unit/stops/test_policy.py::test_a_data_quality_freeze_holds_the_stop`
    - `tests/unit/stops/test_policy.py::test_a_long_stop_never_moves_down`
    - `tests/unit/stops/test_policy.py::test_a_position_whose_stop_is_on_the_wrong_side_cannot_exist`
    - `tests/unit/stops/test_policy.py::test_a_proposal_cannot_be_built_without_a_reason`
    - `tests/unit/stops/test_policy.py::test_a_short_stop_never_moves_up`
    - `tests/unit/stops/test_policy.py::test_a_stop_beyond_the_market_is_refused`
    - `tests/unit/stops/test_policy.py::test_a_stop_inside_the_minimum_distance_holds`
    - `tests/unit/stops/test_policy.py::test_a_sub_threshold_improvement_holds`
    - `tests/unit/stops/test_policy.py::test_a_tightening_anchor_moves_the_stop`
    - `tests/unit/stops/test_policy.py::test_an_anchor_from_the_future_is_never_used`
    - `tests/unit/stops/test_policy.py::test_every_proposal_carries_a_reason_including_holds`
    - `tests/unit/stops/test_policy.py::test_the_buffer_cannot_push_a_stop_past_the_monotonic_rule`
    - `tests/unit/stops/test_policy.py::test_the_noise_buffer_pushes_the_stop_away_from_the_anchor`
    - `tests/unit/stops/test_policy.py::test_the_same_anchor_is_used_once_it_is_knowable`
    - `tests/unit/stops/test_replay.py::test_a_naive_baseline_still_may_not_widen`
    - `tests/unit/stops/test_replay.py::test_a_path_that_never_hits_the_stop_reports_no_exit`
    - `tests/unit/stops/test_replay.py::test_a_position_that_never_stopped_has_no_holding_time`
    - `tests/unit/stops/test_replay.py::test_a_replay_is_deterministic`
    - `tests/unit/stops/test_replay.py::test_a_short_position_records_the_excursion_the_other_way_round`
    - `tests/unit/stops/test_replay.py::test_a_short_position_replays_symmetrically`
    - `tests/unit/stops/test_replay.py::test_a_stop_that_was_right_does_not_count_as_premature`
    - `tests/unit/stops/test_replay.py::test_a_stopped_position_reports_when_it_ended`
    - `tests/unit/stops/test_replay.py::test_no_anchor_kind_derives_a_stop_from_price_alone`
    - `tests/unit/stops/test_replay.py::test_realized_r_is_net_of_fees_and_slippage`
    - `tests/unit/stops/test_replay.py::test_the_data_quality_freeze_fires_in_a_replay`
    - `tests/unit/stops/test_replay.py::test_the_exit_uses_the_executable_price_not_the_requested_stop`
    - `tests/unit/stops/test_replay.py::test_the_naive_baseline_moves_more_often_than_the_structural_one`
    - `tests/unit/stops/test_replay.py::test_the_naive_baselines_are_comparable_on_one_path`
    - `tests/unit/stops/test_replay.py::test_the_premature_rate_is_never_reported_without_realized_r`
    - `tests/unit/stops/test_replay.py::test_the_premature_stop_metric_counts_targets_reached_after_the_stop`
    - `tests/unit/stops/test_replay.py::test_the_replay_counts_why_the_policy_held`
    - `tests/unit/stops/test_replay.py::test_the_replay_records_the_excursion_the_position_saw`
    - `tests/unit/stops/test_replay.py::test_the_stops_package_cannot_consult_a_clock`
- **Code:**
    - `src/channelflow/stops/__init__.py`
    - `src/channelflow/stops/models.py`
    - `src/channelflow/stops/policy.py`
    - `src/channelflow/stops/replay.py`
- **Outcomes:** [[OUT-2026-09-08-implement-adaptive-stops]], [[OUT-2026-09-08-spec-adaptive-stops]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
