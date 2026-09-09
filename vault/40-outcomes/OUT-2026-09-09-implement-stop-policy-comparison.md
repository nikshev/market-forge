---
id: OUT-2026-09-09-implement-stop-policy-comparison
step: implement
records: [REQ-EXP-017]
commit: null
---

## What was done

`channelflow.research.stop_policies`: EXP-017's seven policies, twelve metrics,
seven ablations and its `NO_EDGE` verdict, all through [[REQ-WP-020]]'s replay.
24 tests across two modules, twenty-three mutations, all caught.

## A gate that could not fire

`PricePoint` has carried `data_quality_ok` since the replay was written.
`StopPolicy.propose` has always accepted one. The replay never passed it between
them, so PRD §44A.18's data-quality freeze could not fire on any replayed path —
in the one place a counterfactual evaluation exists to make policy behaviour
observable. It is connected now, with a test that freezes every instant of a
path and asserts the policy held on all of them.

The same change added the walk to `StopPolicyOutcome` ([[ADR-052]]). Four of
EXP-017's twelve metrics — the favourable and adverse excursions, the holding
time, and the two stop-distance quantiles — describe the journey rather than the
exit, and the replay is the only place holding the path and the position's side
together. Computing an excursion outside it means re-deriving that convention,
and a sign error there swaps the position's best moment with its worst while
both numbers stay entirely plausible. A short-position test is the control.

## Four survivors

Two were fixture blindness of the usual kind. Nothing pinned that the "best
simpler policy" excludes the engine — with the engine in its own rival list it
is the best of them by construction and the margin is exactly zero — and nothing
asserted that the median and the 95th-percentile stop distance are two different
numbers, which is the whole reason §44A asks for both.

The third was a badly aimed mutation rather than a gap, and worth recording
because the shape recurs: the mark-out's adverse slippage was inserted after the
gross move had already been computed from the unmutated price, so with a zero
fee it changed nothing at all and the mutant "survived" without ever exercising
the property. Moved to the line that reads the price, it changes the result. The
test now pins both halves — a stop's slippage changes nothing on a path that
never hit its stop, and a taker fee lowers the number.

The fourth was the profit factor over no losses. The engine's own arm wins every
trade on the shakeout fixture, so the case existed all along and no test had
looked at it.

## What was decided

- **A path that never stopped is marked out at its last price**, charged fees
  and not a stop's adverse slippage. Dropping it lets a policy that never exits
  report no losses and win every comparison; charging it for a fill it never
  took is the opposite error.
- **The premature-stop rate is a property, not a field.** §44A.29's warning only
  stops being advice when the number cannot be lifted out on its own.
- **An ablation delta may be negative**, and one of them is: on a clean trend,
  removing the volatility noise floor improves the engine, because the buffer
  widens the stop and the wider stop exits later on the way down.
- **The burden is on the engine.** It has to beat the best of the six simpler
  policies by a declared floor on the same entries after costs.

## Mutation results

Twenty-three mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A policy is dropped | `test_all_seven_policies_the_prd_names_are_compared` |
| An ablation is dropped | `test_all_seven_ablations_the_prd_names_are_run` |
| The premature rate over no stop-outs is zero | `test_a_policy_that_never_stopped_out_has_no_premature_rate` |
| The engine is accepted without a margin | `test_an_engine_that_only_looks_better_is_rejected` |
| The engine ranks among its own rivals | `test_an_engine_that_earns_its_complexity_is_accepted` |
| The verdict compares the engine against itself | `test_an_engine_that_earns_its_complexity_is_accepted` |
| A duplicate entry is accepted | `test_the_same_signal_twice_is_refused` |
| Reports over different entries may be compared | `test_reports_over_different_entries_cannot_be_compared` |
| An unknown capability is accepted | `test_a_capability_the_engine_does_not_have_is_refused` |
| The channel anchor survives its ablation | `test_a_capability_that_is_off_neither_vetoes_nor_supplies_a_level` |
| The swing anchor survives its ablation | `test_a_capability_that_is_off_neither_vetoes_nor_supplies_a_level` |
| A veto does not empty the anchors | `test_a_capability_that_is_off_neither_vetoes_nor_supplies_a_level` |
| The noise floor is not removed by its ablation | `test_a_capability_that_is_off_neither_vetoes_nor_supplies_a_level` |
| An unstopped path is dropped rather than marked out | `test_a_path_that_never_stopped_is_marked_out_rather_than_dropped` |
| The mark-out pays a stop's slippage | `test_a_path_that_never_stopped_is_marked_out_rather_than_dropped` |
| The mark-out pays no fees | `test_a_path_that_never_stopped_is_marked_out_rather_than_dropped` |
| The improvement floor may be zero | `test_the_improvement_floor_is_required_and_positive` |
| The 95th percentile is the median | `test_the_stop_distance_quantiles_are_two_different_numbers` |
| The regime split is not the median | `test_every_primary_metric_the_prd_names_is_reported` |
| The profit factor over no losses is zero | `test_a_policy_that_never_lost_has_no_profit_factor` |
| The replay ignores the data-quality flag | `test_the_data_quality_freeze_fires_in_a_replay` |
| The excursion uses the long convention for a short | `test_a_short_position_records_the_excursion_the_other_way_round` |
| An unfinished path reports a holding time | `test_a_position_that_never_stopped_has_no_holding_time` |

## What is still open

- **No policy is selected for production.** The two fixtures are analytic: one
  is a path with shakeouts placed exactly where a veto can save the position,
  the other a clean trend where the engine's machinery has nothing to do. They
  establish that the comparison can conclude either way, not what it concludes
  on real paths.
- **The improvement floor is unvalidated** and the verdict turns on it: the same
  entries give `EDGE` at 0.05R and `NO_EDGE` at 0.5R.
- **Slippage is still modelled as a constant** ([[ADR-031]]). EXP-017 asks for
  the worst gap or slippage event among its tail metrics, and a constant cannot
  produce one — the reported worst slippage is the model's own number.
- **The regime split is by the paths' own average noise distance.** That is a
  proxy for volatility regime, not a regime classifier.
