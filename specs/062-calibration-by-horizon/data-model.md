# Phase 1 — Data model

## `HorizonSlice`

| Field | Meaning |
|---|---|
| `horizon_ns` | the horizon these rows share |
| `observations` | how many rows fell in it |
| `curve` | the reliability curve, or `None` when the slice is too thin |
| `reason` | why there is no curve, including the count |

`curve` is `None` rather than an empty `Calibration`: absent reliability and poor
reliability are different facts, and this is the third place in the repository
that distinction has had to be made explicit.

## `HorizonCalibration`

`slices` by horizon, `pooled`, and the `target` the probabilities were about.

`pooled` is exactly what `calibration()` returns over the same inputs — beside
the slices, never instead of them.
