---
id: OUT-2026-09-09-implement-channel-comparison
step: implement
records: [REQ-EXP-001]
commit: null
---

## What was done

`channelflow.research.channel_comparison`: EXP-001's five models, seven metrics,
one series. 16 tests. This is the first of the seventeen experiments to close.

## Six of eleven mutations survived the first sweep

Every one of them was the same failure: a fixture that could not tell two
definitions apart.

- **Coverage backwards instead of forwards** — on a smooth series the two are
  nearly the same number, and every fixture was smooth. A flat series that breaks
  into a hard trend separates them: 31.7% forward against 49.2% backward, because
  the backward window is the bars the channel was fitted on.
- **Stability as the average instead of the dispersion** — the short-lookback
  fixture had both a higher mean and a higher spread, so either definition
  ranked it the same way. A steady trend has a large average slope and almost no
  variation; an oscillation has the reverse.
- **A degenerate channel counted as covered** — no fixture produced a zero-width
  band until one was asked for.
- **The cost figure counting fits instead of cost** — the test asserted only that
  it was positive and stable. The quantile model costs two orders of magnitude
  more per fit than the least-squares one, and now the test says so.
- **Expectancy including in-sample confirmations** — the test compared bar counts
  rather than trade counts. It now compares the experiment's trades against every
  confirmation in the whole run.
- **The costs refusal dropped** — the downstream refusal in [[REQ-BT-001]] caught
  it whenever a model traded, so the early one looked redundant. Tested with a
  model set that trades nothing, only the early refusal can fire.

## What was decided

- **A false perfect touch is measured against the last fit** ([[ADR-049]]) —
  what a chart shows — not against any pair of fits.
- **Cost is an operation count**, for the same reason the perturbation lattice in
  [[ADR-041]] is deterministic.
- **All-ambiguous outcomes report absent expectancy with a reason.** PRD §40's
  rule would otherwise be undone one layer up, by an exception where a finding
  belongs.

## Mutation results

Eleven mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The series-length guard is dropped | `test_a_series_too_short_for_the_longest_lookback_is_refused` |
| Coverage looks backwards | `test_coverage_looks_forward_from_each_fit` |
| A degenerate channel counts as covered | `test_a_degenerate_channel_has_no_coverage_rather_than_perfect_coverage` |
| Stability is the mean, not the dispersion | `test_stability_is_the_dispersion_not_the_average` |
| False touches compare the channel with itself | `test_a_repainted_touch_is_counted_as_false` |
| The cost figure is the same for every model | `test_the_cost_figure_separates_the_expensive_model_from_the_cheap_one` |
| Expectancy includes in-sample confirmations | `test_expectancy_counts_only_out_of_sample_confirmations` |
| No setups reports zero expectancy | `test_a_model_with_no_setups_reports_absent_expectancy` |
| A fit failure ends the whole comparison | `test_a_model_that_cannot_fit_is_reported_and_does_not_stop_the_others` |
| The costs refusal is dropped | `test_expectancy_without_costs_is_refused` |
| Unresolvable outcomes are scored anyway | `test_a_model_whose_outcomes_are_all_ambiguous_reports_no_expectancy` |

## What is still open

- **Coverage is not projected along the channel's slope.** The richer measure
  needs the raw log slope, which `ChannelSnapshot` does not carry; PRD §13.7 is
  where a forecast channel belongs.
- **No conclusion is drawn.** The experiment ranks; choosing a production model
  is a decision with more inputs than these seven metrics.
