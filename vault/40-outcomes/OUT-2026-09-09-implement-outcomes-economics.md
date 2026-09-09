---
id: OUT-2026-09-09-implement-outcomes-economics
step: implement
records: [REQ-BT-001]
commit: null
---

## What was done

`channelflow.backtest.outcomes`, `.fills` and `.economics`: PRD §40's outcome
resolution, §25.4's two phase-1 fills, and §25.5's metrics after costs. 25 tests.

[[ADR-009]]'s restriction is lifted on the condition it named for itself, and
[[ADR-048]] is the record.

## A guard that could not fire, hiding one that could

The sweep found one survivor: nulling the touch times when the outcome is
ambiguous changed no test. It could not — the ambiguous branch `break`s before
either time can be set, so the guard was unreachable.

Worse than redundant. While it stood, deleting that `break` also changed no test:
the walk would have continued past the ambiguous bar, found a later touch, and
the guard would have quietly discarded it. Two guards over one property, and the
reachable one was invisible.

The guard is gone. The `break` is the guarantee, and the sweep now mutates it
directly.

## What was decided

- **A touch includes equality with the level.** A strict breach is the
  favourable ordering by one tick, on every trade.
- **A timeout exits at the close**, a target at the target, a stop at the stop.
  An ambiguous trade's return is filled in so the record is complete and
  excluded from every metric so the number is not used.
- **The next-open fill refuses without a next bar.** Falling back to the close
  would fill the last signal of every dataset better than any other, and the
  bias grows with how recently the backtest ends.
- **A zero-loss profit factor is `None`, not infinity.** Infinity reads as a
  spectacular result rather than as a sample with nothing to divide by.
- **The drawdown is of the equity path.** Three losses in a row draw down more
  than the worst of them.

## Mutation results

Fifteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An ambiguous bar resolves to the target | `test_a_bar_containing_both_levels_is_ambiguous` (+1) |
| The ambiguous branch does not stop the walk | `test_an_ambiguous_outcome_claims_neither_touch_time` |
| A touch must strictly breach the level | `test_a_touch_at_exactly_the_level_counts` (+1) |
| The horizon guard is dropped | `test_a_horizon_past_the_data_is_refused` |
| Direction is ignored when resolving | `test_a_short_resolves_by_its_own_direction` |
| The timeout exits at the target | `test_neither_touched_is_a_timeout_with_its_horizon_return` |
| The next-open fill falls back to the close | `test_the_next_open_fill_refuses_without_a_next_bar` |
| Slippage helps the trade | `test_slippage_moves_the_fill_against_the_trade` |
| The cost model is optional after all | `test_metrics_without_a_cost_model_are_refused` |
| The costs are not applied to the returns | `test_the_profit_factor_is_gross_gains_over_gross_losses` (+1) |
| Ambiguous outcomes are included | `test_ambiguous_outcomes_are_excluded_and_counted` (+1) |
| An empty resolved set is reported as zeros | `test_no_resolved_outcome_is_refused` |
| A zero-loss profit factor is infinite | `test_a_run_with_no_losses_reports_no_profit_factor` |
| The drawdown is the worst single trade | `test_the_drawdown_is_of_the_equity_path_not_of_one_trade` |
| Expectancy ignores the risk unit | `test_expectancy_is_measured_in_units_of_risk` |

## What is still open

- **§25.4's phase-2 fills.** Every economic figure here rests on a market fill.
- **Nothing wires this into the runner yet.** The experiments are the consumers,
  and each supplies its own targets, stops and costs.
