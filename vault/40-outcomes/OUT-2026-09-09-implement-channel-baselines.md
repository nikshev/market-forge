---
id: OUT-2026-09-09-implement-channel-baselines
step: implement
records: [REQ-CHAN-001]
commit: null
---

## What was done

Baselines B, C and D — Huber with MAD bands, exact conditional quantiles, and a
local linear trend filter — plus the window rule extracted from baseline A.
16 tests.

## The sweep found an estimator, not a test

Four mutations survived the first pass, and one of them was not a missing test
at all.

**"The minimum width is not enforced" survived** because a perfectly flat series
was already coming back with a 2.5% channel, so the floor never bound. The floor
was fine. The estimator was wrong: the pinball subgradient is `tau` or `tau - 1`
however small the residual, so the descent oscillated around the solution for
ever, and on flat data that oscillation *was* the band. Smoothing the gradient
made it diverge instead — the smoothing turns the loss locally quadratic with
curvature `1/smoothing`, and the step was five thousand times too large for it.

The fix is [[ADR-047]]: enumerate the lines through pairs of points and take the
best. The pinball loss is piecewise linear in two coefficients, so its minimum
sits at a vertex; 1,770 candidates at a lookback of sixty, two milliseconds, and
three research defaults — step, smoothing, iterations — disappear.

**"The Kalman band ignores the innovations" survived on floating-point dust.**
With a constant band both series produced 2.5632701681147116 and
2.5632701681147165, and `wide > narrow` accepted the second as evidence. The
test now asks for a margin.

**"The Kalman filter sees the whole window at once" survived** because a filter
that ignores its observations passes every invariance test — it returns the same
thing whatever arrives, which is exactly what "no later bar changes an earlier
state" asks for. A test that the centre tracks the last price and the slope
takes the trend's sign is what says it followed the data.

**"The bands use the standard deviation, not the MAD" survived** because only
the centre's robustness was tested. A robust centre with a standard-deviation
band is half a robust channel: the centre holds, the boundaries jump, and the
zones move anyway.

## What was decided

- **The quantile fit is exact** ([[ADR-047]]), with ties broken on the
  coefficients rather than on enumeration order.
- **Baseline D is a written-out loop**, because the loop is the guarantee: there
  is nowhere in it a later observation could enter.
- **Each model names what it cannot compute.** Baseline A's coverage submetrics
  do not transfer, and reporting them anyway would compare models by comparing
  quality definitions.

## Mutation results

Fourteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The robust fit is plain least squares | `test_the_robust_centre_ignores_a_wick_the_least_squares_centre_chases` |
| The bands use the standard deviation, not the MAD | `test_the_robust_band_does_not_blow_out_on_one_wick` |
| The short-window guard is dropped | `test_every_baseline_refuses_a_short_window` (+1) |
| Unfinalized bars are used | `test_unfinalized_bars_are_excluded` |
| Bars after the instant are used | `test_the_hard_invariant_holds` (+1) |
| Quantile crossing is not corrected | `test_quantile_lines_that_cross_are_reordered` |
| The minimum width is not enforced | `test_a_flat_series_still_has_the_minimum_width` |
| The slope-consistency submetric is dropped | `test_slope_disagreement_between_the_quantiles_is_reported` |
| The quantile fit is the conditional mean | `test_the_quantile_channel_can_be_asymmetric` |
| The quantile tie-break is dropped | `test_a_tied_quantile_fit_is_resolved_by_a_stated_rule` |
| The Kalman band ignores the innovations | `test_the_kalman_band_widens_with_the_innovations` |
| The Kalman filter sees the whole window at once | `test_the_kalman_filter_tracks_the_series_it_is_given` (+1) |
| State uncertainty is not reported | `test_the_kalman_channel_reports_its_state_uncertainty` |
| A backward pass is added | `test_the_kalman_module_contains_no_backward_pass` |

## What is still open

- **Theil-Sen and RANSAC**, named in `huber.py` as unbuilt.
- **§13.6's experimental robust trend filter**, deliberately out of scope.
- **Nothing selects between the baselines yet.** [[REQ-EXP-001]] is the
  comparison, and it is next.
