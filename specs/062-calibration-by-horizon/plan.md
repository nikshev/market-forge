# Implementation Plan: Calibration per horizon

**Branch**: `wp-023-calibration-by-horizon` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

`calibration_by_horizon(rows, predicted, *, target, minimum_observations)`:
group by each row's own horizon, report a curve where the slice is thick enough
and a stated reason where it is not, and carry the pooled figure beside them.

`calibration()` is unchanged and is what produces both the slices and the pooled
number, so a reader comparing an old report against a new one compares like with
like.

## Technical Context

**Language/Version**: Python 3.12 · **Dependencies**: none new · **Storage**: none

**Testing**: pytest with `@pytest.mark.trace("REQ-WP-023")` and a mutation sweep.

**Constraints**: the threshold is the caller's (Principle X); the horizon is the row's own.

**Scale/Scope**: one function and two values in `models/metrics.py`.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **V. Calibration, not accuracy** | This is that principle applied at the resolution a forecast is used at. | **Pass, and it is the point.** |
| **X. Thresholds are configuration** | `minimum_observations` decides which findings are visible. | **Pass.** It is a required argument, not a default. |
| **VI. Every feature is documented** | An unmeasured slice states its count and its reason. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/models/metrics.py    # + LabelLike, RowWithLabel, HorizonSlice,
                                     #   HorizonCalibration, calibration_by_horizon
tests/unit/models/test_calibration_by_horizon.py   # NEW
```

**Structure Decision**: it lives beside `calibration()`, which it calls twice per
report. The row shape arrives as a Protocol rather than an import — a metrics
module that imported the dataset package would run the dependency backwards, and
this needs two fields out of a model with a dozen. `dataset.leakage` already does
exactly this with `RowLike`.
