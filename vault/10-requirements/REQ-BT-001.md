---
id: REQ-BT-001
title: Signal outcomes, fill models and economic metrics
type: work-package
prd_ref: "§40 Signal Outcome Definitions, §25.4 Fill models, §25.5 Metrics"
prd_lines: "4249-4290, 5293-5312"
phase: null
status: implemented
depends_on: ["REQ-WP-007", "REQ-WP-010"]
tags: []
hard_gated: false
---

## Requirement

PRD §40, **Signal Outcome Definitions**:

> Every signal later gets `SignalOutcome`, separate from original immutable
> signal.

```python
class SignalOutcome:
    signal_id: UUID
    horizon_end: datetime
    first_target_time: datetime | None
    first_invalidation_time: datetime | None
    mfe_pct: float
    mae_pct: float
    return_h: float
    outcome: Literal["target", "stop", "timeout", "ambiguous"]
```

> If bar data cannot determine whether stop/target happened first inside one
> bar, mark `ambiguous` unless lower-timeframe/tick replay resolves it.
>
> **Never choose the favorable ordering.**

PRD §25.4, **Fill models**:

> Phase 1:
> - market-at-next-bar-open;
> - market-at-signal-close + configurable slippage.
>
> Phase 2:
> - trade-through limit fill approximation;
> - L2-aware simulation.

PRD §25.5's per-setup metrics, of which these need an outcome and a fill:

> win rate; average return; median return; expectancy in R; profit factor;
> Sharpe; Sortino; max drawdown; average MFE; average MAE; target hit
> probability; fees; slippage; funding cost; DEX gas where applicable.

PRD §41 rule 9: **"Fees/slippage must be included in economic evaluation."**

## Acceptance

Outcomes (§40):

- a `SignalOutcome` carries every field §40 lists, and is separate from the
  signal it describes;
- `outcome` is one of `target`, `stop`, `timeout`, `ambiguous`;
- a bar that touches both the target and the stop resolves to `ambiguous`,
  never to whichever came out better;
- `mfe_pct` and `mae_pct` are measured over the horizon from the fill price;
- `first_target_time` and `first_invalidation_time` are the first touch of each,
  or absent;
- an outcome is refused when the horizon extends past the available bars.

Fill models (§25.4):

- market-at-next-bar-open is implemented;
- market-at-signal-close with a configurable slippage is implemented;
- slippage moves the fill against the trade in both directions;
- the phase-2 models are named as unbuilt wherever fills are described;
- a fill that cannot be made — no next bar — is refused rather than assumed.

Economics (§25.5, §41 rule 9):

- win rate, average and median return, expectancy in R, profit factor, Sharpe,
  Sortino, maximum drawdown, average MFE, average MAE and target-hit
  probability are computed from resolved outcomes;
- every one of them is computed **after** fees and slippage, and the costs
  applied are reported alongside;
- an economic metric requested without a cost model is refused;
- `ambiguous` outcomes are excluded from economic metrics and their count is
  reported.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-033-outcomes-economics]]
- **Tests:**
    - `tests/unit/backtest/test_economics.py::test_a_run_with_no_losses_reports_no_profit_factor`
    - `tests/unit/backtest/test_economics.py::test_ambiguous_outcomes_are_excluded_and_counted`
    - `tests/unit/backtest/test_economics.py::test_every_section_25_5_metric_is_reported`
    - `tests/unit/backtest/test_economics.py::test_expectancy_is_measured_in_units_of_risk`
    - `tests/unit/backtest/test_economics.py::test_metrics_without_a_cost_model_are_refused`
    - `tests/unit/backtest/test_economics.py::test_no_resolved_outcome_is_refused`
    - `tests/unit/backtest/test_economics.py::test_raising_the_costs_lowers_the_expectancy`
    - `tests/unit/backtest/test_economics.py::test_the_backtest_package_consults_no_clock`
    - `tests/unit/backtest/test_economics.py::test_the_costs_are_reported_with_the_metrics`
    - `tests/unit/backtest/test_economics.py::test_the_drawdown_is_of_the_equity_path_not_of_one_trade`
    - `tests/unit/backtest/test_economics.py::test_the_metrics_are_computed_after_costs`
    - `tests/unit/backtest/test_economics.py::test_the_profit_factor_is_gross_gains_over_gross_losses`
    - `tests/unit/backtest/test_economics.py::test_the_same_outcomes_report_identically_twice`
    - `tests/unit/backtest/test_outcomes.py::test_a_bar_containing_both_levels_is_ambiguous`
    - `tests/unit/backtest/test_outcomes.py::test_a_horizon_past_the_data_is_refused`
    - `tests/unit/backtest/test_outcomes.py::test_a_short_resolves_by_its_own_direction`
    - `tests/unit/backtest/test_outcomes.py::test_a_stop_reached_first_is_a_stop`
    - `tests/unit/backtest/test_outcomes.py::test_a_target_reached_first_is_a_target`
    - `tests/unit/backtest/test_outcomes.py::test_a_touch_at_exactly_the_level_counts`
    - `tests/unit/backtest/test_outcomes.py::test_an_ambiguous_outcome_claims_neither_touch_time`
    - `tests/unit/backtest/test_outcomes.py::test_neither_touched_is_a_timeout_with_its_horizon_return`
    - `tests/unit/backtest/test_outcomes.py::test_slippage_moves_the_fill_against_the_trade[long-100.60049999999998]`
    - `tests/unit/backtest/test_outcomes.py::test_slippage_moves_the_fill_against_the_trade[short-100.3995]`
    - `tests/unit/backtest/test_outcomes.py::test_the_next_open_fill_is_the_next_bars_open`
    - `tests/unit/backtest/test_outcomes.py::test_the_next_open_fill_refuses_without_a_next_bar`
    - `tests/unit/backtest/test_outcomes.py::test_the_phase_two_fills_are_named_as_unbuilt`
- **Code:**
    - `src/channelflow/backtest/__init__.py`
    - `src/channelflow/backtest/economics.py`
    - `src/channelflow/backtest/fills.py`
    - `src/channelflow/backtest/outcomes.py`
- **Outcomes:** [[OUT-2026-09-09-implement-outcomes-economics]], [[OUT-2026-09-09-plan-outcomes-economics]], [[OUT-2026-09-09-spec-outcomes-economics]]
<!-- trace:end -->

## Notes

Extracted on 2026-09-09. [[ADR-009]] deliberately left backtest v1 without
returns because §40 and §25.4 were unbuilt, and named exactly this as what would
lift the restriction. Nine of the seventeen `REQ-EXP-*` experiments ask for
expectancy, profit factor or "incremental value after costs", so this is their
common blocker.

§25.4's phase-2 fills and §42's point-in-time universe are out of scope; both
are separate PRD sections with their own requirements owed.
