---
id: OUT-2026-09-09-implement-lead-lag-value
step: implement
records: [REQ-EXP-010]
commit: null
---

## What was done

`channelflow.research.lead_lag_value`: EXP-010's out-of-sample study, with
latency and costs. 16 tests, ten mutations, all caught.

## A fixture that could not reward a correct prediction

The first series jumped one bar after each signal — which is the bar the fill
happens on. The trade entered at the post-jump price and caught nothing, so a
perfectly predictive signal reported an expectancy of −0.11R and the control test
failed.

The move now lands two bars later. A fixture that cannot reward a correct
prediction cannot distinguish a working study from a broken one, and both would
have looked the same.

## Five survivors, five different blind spots

- **The threshold chosen on every signal instead of the training half** — the
  test compared in-sample against out-of-sample trade counts, which stayed
  ordered either way. It now checks the in-sample count against the number of
  in-sample signals.
- **The costs refusal** was a restatement of the economics layer's until it was
  tested with no signals at all, where only the outer one can fire.
- **Direction ignored** — every fixture was long, so a target computed as if
  every trade were long was indistinguishable. A falling series with short
  signals separates them.
- **All-ambiguous outcomes** would have raised out of the metric layer instead of
  reporting.
- **The threshold scan keeping the last candidate** rather than the best — every
  threshold scored identically on the fixture, so "best" and "last" agreed until
  the test pinned which one is kept.

## What was decided

- **Ties keep the first threshold.** Equal scores mean the filter did not matter,
  and the narrower one says so.
- **`NO_EDGE` covers the all-ambiguous case**, rather than an exception.
- **The import ban extends [[ADR-040]]** to this study, checked over import
  lines.

## Mutation results

Ten mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The latency is not applied | `test_latency_can_destroy_the_edge` |
| A negative latency is accepted | `test_a_negative_latency_is_refused` |
| The threshold is chosen on every signal | `test_the_in_sample_score_counts_only_in_sample_signals` |
| The out-of-sample score uses the training half | `test_the_threshold_is_chosen_in_sample_and_scored_out_of_sample` |
| The split guard is dropped | `test_signals_on_one_side_of_the_split_cannot_be_validated` |
| The verdict ignores the out-of-sample result | `test_noise_returns_no_edge_and_raises_nothing` |
| The costs refusal is dropped | `test_the_costs_refusal_fires_before_anything_is_scored` |
| The direction is ignored | `test_a_short_divergence_is_traded_as_a_short` |
| Ambiguous-only outcomes are scored | `test_outcomes_that_are_all_ambiguous_report_rather_than_raise` |
| The best threshold is the last tried | `test_the_first_threshold_that_scores_best_is_kept` |

## What is still open

- **Sub-bar latency.** Bars are the resolution here; PRD §40's tick replay is
  what a finer one would need.
- **Nothing produces the signals.** [[REQ-WP-016]] gives the basis; reading it as
  a direction is the caller's judgement.
