---
id: REQ-CHAN-001
title: Channel baselines B, C and D — robust, quantile and Kalman
type: work-package
prd_ref: "§13.3 Baseline B, §13.4 Baseline C, §13.5 Baseline D"
prd_lines: "1116-1163"
phase: null
status: implemented
depends_on: ["REQ-WP-006"]
tags: []
hard_gated: false
---

## Requirement

PRD §13.3, **Baseline B — Robust Regression Channel**:

> Candidate estimators:
> - Huber regression;
> - Theil-Sen;
> - RANSAC only as experimental due discontinuous model changes.
>
> Goal: reduce sensitivity to liquidation wicks/outliers.

PRD §13.4, **Baseline C — Quantile Regression Channel**:

> Fit conditional quantiles directly:
> - q10 lower;
> - q50 center;
> - q90 upper.
>
> This supports asymmetric channels.
>
> Required checks:
> - quantile crossing correction;
> - minimum width;
> - slope consistency;
> - numerical stability.

PRD §13.5, **Baseline D — Kalman Local Linear Trend**:

```text
state:       level_t, slope_t
observation: log_price_t = level_t + noise
```

> Use recursive filtering only. Smoother that uses future observations is
> forbidden for live-compatible features.

> Potential outputs: level; slope; state uncertainty; adaptive band based on
> innovation variance.

## Acceptance

Every baseline:

- produces the same `ChannelSnapshot` shape as [[REQ-WP-006]]'s baseline A,
  naming its own model and version;
- filters its own window by `as_of`, so a caller passing later bars gets the
  same answer as one who does not;
- refuses rather than fitting on fewer bars than its lookback.

Baseline B (§13.3):

- Huber regression with MAD-derived bands is implemented;
- a single extreme wick moves the fitted centre materially less than it moves
  baseline A's;
- the estimators §13.3 lists but this does not implement are named as unbuilt
  wherever the baseline is described.

Baseline C (§13.4):

- conditional q10, q50 and q90 are fitted directly, producing an asymmetric
  channel;
- crossing is corrected: the fitted quantiles are ordered after the fit even
  when the raw solutions cross;
- a minimum width is enforced and configurable;
- slope consistency is checked across the three quantiles and reported;
- a degenerate or numerically unstable fit is refused rather than returned.

Baseline D (§13.5):

- a local linear trend filter over `level` and `slope`, recursive only;
- no code path consults an observation later than the instant being filtered,
  and a test asserts it over the source;
- state uncertainty is reported;
- the band is derived from innovation variance and widens when innovations grow.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-032-channel-baselines]]
- **Tests:**
    - `tests/unit/channels/test_baselines.py::test_a_flat_series_still_has_the_minimum_width`
    - `tests/unit/channels/test_baselines.py::test_a_kalman_state_never_changes_when_later_bars_arrive`
    - `tests/unit/channels/test_baselines.py::test_a_tied_quantile_fit_is_resolved_by_a_stated_rule`
    - `tests/unit/channels/test_baselines.py::test_crossed_quantiles_come_back_ordered`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_ignores_bars_after_the_instant[fitter0]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_ignores_bars_after_the_instant[fitter1]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_ignores_bars_after_the_instant[fitter2]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_names_itself[fitter0]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_names_itself[fitter1]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_names_itself[fitter2]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_refuses_a_short_window[fitter0]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_refuses_a_short_window[fitter1]`
    - `tests/unit/channels/test_baselines.py::test_every_baseline_refuses_a_short_window[fitter2]`
    - `tests/unit/channels/test_baselines.py::test_no_baseline_consults_a_clock`
    - `tests/unit/channels/test_baselines.py::test_quantile_lines_that_cross_are_reordered`
    - `tests/unit/channels/test_baselines.py::test_slope_disagreement_between_the_quantiles_is_reported`
    - `tests/unit/channels/test_baselines.py::test_the_kalman_band_widens_with_the_innovations`
    - `tests/unit/channels/test_baselines.py::test_the_kalman_channel_reports_its_state_uncertainty`
    - `tests/unit/channels/test_baselines.py::test_the_kalman_filter_tracks_the_series_it_is_given`
    - `tests/unit/channels/test_baselines.py::test_the_kalman_module_contains_no_backward_pass`
    - `tests/unit/channels/test_baselines.py::test_the_quantile_channel_can_be_asymmetric`
    - `tests/unit/channels/test_baselines.py::test_the_robust_band_does_not_blow_out_on_one_wick`
    - `tests/unit/channels/test_baselines.py::test_the_robust_centre_ignores_a_wick_the_least_squares_centre_chases`
    - `tests/unit/channels/test_baselines.py::test_the_unbuilt_estimators_are_named_in_the_module`
- **Code:**
    - `src/channelflow/channels/__init__.py`
    - `src/channelflow/channels/huber.py`
    - `src/channelflow/channels/kalman.py`
    - `src/channelflow/channels/quantile.py`
    - `src/channelflow/channels/window.py`
- **Outcomes:** [[OUT-2026-09-09-implement-channel-baselines]], [[OUT-2026-09-09-plan-channel-baselines]], [[OUT-2026-09-09-spec-channel-baselines]]
<!-- trace:end -->

## Notes

Extracted on 2026-09-09 because [[REQ-EXP-001]] compares five channel models and
only baseline A existed. §13.3 to §13.5 specify the other three in full, so
nothing here is derived.

§13.6's experimental robust trend filter is deliberately out of scope: the PRD
marks it optional and its "must not use centered filters" caveat is
[[REQ-NRT-D]]'s subject, already enforced.
