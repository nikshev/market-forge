---
id: REQ-EXP-017
title: Adaptive stop-management policy
type: experiment
prd_ref: "EXP-017 Adaptive stop-management policy"
prd_lines: "5252-5292"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Compare position-management policies on the exact same immutable entry signals:

1. fixed initial stop only;
2. naive fixed-percent trailing stop;
3. ATR/volatility trailing stop;
4. confirmed-swing structural trailing stop;
5. channel-conditioned structural stop;
6. structural stop + order-flow confirmation;
7. full Adaptive Stop Management Engine.

Primary metrics:

- expectancy after fees/slippage;
- realized R multiple;
- profit factor;
- stop-out rate;
- percentage of trades stopped before later reaching original target;
- give-back from MFE to realized exit;
- MAE before stop;
- median/95p stop distance;
- average holding time;
- turnover / stop modification count;
- tail loss / worst gap or slippage event;
- regime stability.

Ablations:

- remove swing confirmation;
- remove volatility/noise floor;
- remove order-flow veto;
- remove channel context;
- remove extremum/turning-point forecast;
- remove DeFi/cross-venue context;
- remove hysteresis/cooldown.

The experiment must be able to conclude `NO_EDGE`: a sophisticated trailing policy is rejected if it only looks better visually but does not improve OOS economics or risk-adjusted outcomes.

## Acceptance

- the seven policies (fixed initial stop; naive fixed-percent trailing; ATR/volatility trailing; confirmed-swing structural trailing; channel-conditioned structural stop; structural stop + order-flow confirmation; full Adaptive Stop Management Engine) are compared on identical immutable entry signals;
- primary metrics are reported: expectancy after fees/slippage, realized R multiple, profit factor, stop-out rate, percentage of trades stopped before later reaching original target, give-back from MFE to realized exit, MAE before stop, median/95p stop distance, average holding time, turnover/stop modification count, tail loss/worst gap or slippage event, regime stability;
- the listed ablations (swing confirmation, volatility/noise floor, order-flow veto, channel context, extremum/turning-point forecast, DeFi/cross-venue context, hysteresis/cooldown) are each removed and evaluated in turn;
- the experiment can conclude `NO_EDGE` and reject the policy if it only looks better visually without improving OOS economics or risk-adjusted outcomes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-050-stop-policy-comparison]]
- **Tests:**
    - `tests/unit/research/test_stop_policies.py::test_a_capability_that_is_off_neither_vetoes_nor_supplies_a_level`
    - `tests/unit/research/test_stop_policies.py::test_a_capability_the_engine_does_not_have_is_refused`
    - `tests/unit/research/test_stop_policies.py::test_a_path_that_never_stopped_is_marked_out_rather_than_dropped`
    - `tests/unit/research/test_stop_policies.py::test_a_policy_that_never_lost_has_no_profit_factor`
    - `tests/unit/research/test_stop_policies.py::test_a_policy_that_never_stopped_out_has_no_premature_rate`
    - `tests/unit/research/test_stop_policies.py::test_all_seven_ablations_the_prd_names_are_run`
    - `tests/unit/research/test_stop_policies.py::test_all_seven_policies_the_prd_names_are_compared`
    - `tests/unit/research/test_stop_policies.py::test_an_ablation_can_come_out_either_way`
    - `tests/unit/research/test_stop_policies.py::test_an_engine_that_earns_its_complexity_is_accepted`
    - `tests/unit/research/test_stop_policies.py::test_an_engine_that_only_looks_better_is_rejected`
    - `tests/unit/research/test_stop_policies.py::test_every_policy_runs_over_the_exact_same_entry_signals`
    - `tests/unit/research/test_stop_policies.py::test_every_primary_metric_the_prd_names_is_reported`
    - `tests/unit/research/test_stop_policies.py::test_reports_over_different_entries_cannot_be_compared`
    - `tests/unit/research/test_stop_policies.py::test_the_floor_decides_the_verdict`
    - `tests/unit/research/test_stop_policies.py::test_the_improvement_floor_is_required_and_positive`
    - `tests/unit/research/test_stop_policies.py::test_the_premature_stop_rate_cannot_be_read_without_realized_expectancy`
    - `tests/unit/research/test_stop_policies.py::test_the_same_signal_twice_is_refused`
    - `tests/unit/research/test_stop_policies.py::test_the_stop_distance_quantiles_are_two_different_numbers`
    - `tests/unit/research/test_stop_policies.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/stop_policies.py`
- **Outcomes:** [[OUT-2026-09-09-implement-stop-policy-comparison]], [[OUT-2026-09-09-plan-stop-policy-comparison]], [[OUT-2026-09-09-spec-stop-policy-comparison]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
