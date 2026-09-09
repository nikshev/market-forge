---
id: OUT-2026-09-09-implement-corridor-calibration
step: implement
records: [REQ-EXP-009]
commit: null
---

## What was done

`channelflow.research.corridor_calibration`, and the raw log slope on every
channel snapshot. 13 tests, ten mutations, all caught.

## Two survivors the aggregate report could not show

**Pooling the folds** changed nothing, because every fixture was homogeneous:
coverage was the same in each quarter, so per-fold and pooled agreed. A series
that is quiet for two hundred bars and volatile for two hundred more separates
them — and that difference is the failure the experiment exists to find, since a
corridor that works in a calm quarter and fails in a loud one is exactly what
"stable" excludes.

**Letting the conformal method calibrate on its own outcome** also changed
nothing observable. It is a leak that makes a corridor widen precisely when it
needs to, reporting coverage no live system could achieve — and in aggregate it
moves the number by less than the noise between fixtures.

It is visible only per instant, so the measurements became public. The test puts
a single ten-percent shock in the series and asserts the conformal width at the
fit whose horizon lands on it is *narrower* than the next fit's: the width may
not react until the error is in the past.

## What was decided

- **`slope_log_per_bar` on the snapshot**, closing [[ADR-049]]'s named gap. The
  quantile baseline's version needed converting from its scaled index — reported
  raw it was eighteen times too small, which showed up as 0.00000 beside three
  baselines agreeing on 0.002.
- **A minimum measurement count.** A seventy-bar series produced exactly one
  measurement and passed the old non-empty guard; a coverage rate over one fit
  is the last fit.
- **The narrowest failure is never offered.** `pick_winner` returns nothing when
  nothing holds, and says why.

## Mutation results

Ten mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| Stability is the mean, not the worst fold | `test_stability_is_per_fold_not_on_average` |
| The narrowest overall wins | `test_with_nothing_stable_there_is_no_winner` (+1) |
| The width tie-break is dropped | `test_a_tie_on_width_is_broken_by_name` |
| An unsupported coverage level is accepted | `test_only_the_prds_coverage_levels_are_accepted` |
| The measurement floor is dropped | `test_a_series_too_short_is_refused` |
| The forecast centre is projected flat | `test_the_forecast_centre_follows_the_channels_slope` |
| Folds are pooled | `test_coverage_is_reported_by_fold_not_pooled` |
| The conformal corridor is the empirical one | `test_the_conformal_corridor_adapts_where_the_others_do_not` |
| The conformal method calibrates on its own outcome | `test_the_conformal_corridor_does_not_calibrate_on_its_own_outcome` |
| The snapshot's raw slope is always zero | `test_the_forecast_centre_follows_the_channels_slope` |

## What is still open

- **The full adaptive conformal scheme**, which §13.8 marks optional.
- **Nothing runs this on real data**, as with every experiment here.
