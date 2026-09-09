---
id: OUT-2026-09-09-implement-extremum-detectors
step: implement
records: [REQ-EXP-011]
commit: null
---

## What was done

`channelflow.research.extremum_detectors`: EXP-011's five methods and five
metrics. 17 tests, ten mutations, all caught.

## A mode that could never fire, and a unit that made sure of it

`CHANNEL_WIDTH_FRACTION` is one of the five methods EXP-011 names. It needs a
channel width, and `DirectionalChangeDetector.on_bar` had no parameter to supply
one — so through the detector the mode raised `ThresholdUnavailable` on every
bar and confirmed nothing, for as long as it has existed.

Adding the parameter was not enough. The policy's `channel_width_pct` was read
as a *fraction of price* while the only producer of that number,
`ChannelSnapshot.width_pct`, is a *percentage*. Wired together they differ by a
hundred: a real 5.5% channel gave a 13,750 bps threshold instead of 137, and the
detector confirmed nothing again — this time reporting "this method found no
extrema", which reads like a finding.

Both are fixed, and the units are now the channel's own.

## Six survivors, and one fixture that could not see

The sweep found six. Five were ordinary: the median regime split, the regime
attribution, the ratio's direction, the lag's floor, and the costs reaching the
expectancy.

The sixth would not fall to a better assertion. Replacing the fitted channel
width with a tiny constant changed nothing measurable, because the fixture was a
smooth sine: it turns twice per period whatever the threshold is, so a sensible
threshold and an absurd one produce the same count. Adding a chop separates them
— 45 confirmations per thousand bars against 235 — and the test now says which
number it expects and why.

## What was decided

- **Nothing is ranked.** The five metrics pull against each other, and a winner
  would hide the trade-off.
- **The regime split is the median**, so it halves any shape; a cut from one
  bar's own volatility lands wherever that bar happened to be.
- **An extremum belongs to the regime it was confirmed in**, not the one it
  happened in.
- **The ratio is busier over quieter**, so it is never below one and a bigger
  number always means less stable.

## Mutation results

Ten mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The channel mode is silently skipped | `test_the_channel_mode_needs_a_channel_and_says_so` |
| The channel width is never fitted | `test_the_channel_mode_uses_the_channels_own_width` |
| Regimes split into fixed halves | `test_the_median_split_divides_the_series_in_half` |
| An extremum is attributed to the wrong regime | `test_extrema_are_attributed_to_both_regimes` |
| The regime ratio is inverted | `test_the_regime_ratio_is_the_busier_over_the_quieter` |
| A method that confirms nothing reports zero | `test_a_method_that_confirms_nothing_says_so` |
| The costs refusal is dropped | `test_the_comparison_without_costs_is_refused` |
| The lag is a constant | `test_a_confirmation_always_lags_its_extremum` |
| The channel width is read as a fraction again | `test_the_channel_width_mode_is_a_fraction_of_the_width` (+1) |
| The expectancy ignores its costs | `test_the_downstream_expectancy_is_after_costs` |

## What is still open

- **No mode is selected for production.** The experiment reports; choosing needs
  more than one series.
- **Prominence is reported where the detector recorded it** and absent where it
  did not; the prominence rule is [[REQ-WP-019]]'s and unchanged here.
