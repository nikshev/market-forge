# Contract — calibration per horizon

```
calibration_by_horizon(rows, predicted, *, target, minimum_observations) -> HorizonCalibration
```

## Guarantees

- one slice per distinct horizon present in the rows, keyed by `horizon_end_ns - as_of_ns`;
- a slice with fewer rows than `minimum_observations` carries no curve and states its count;
- a slice with rows and no positive outcomes carries a curve — it is measured, and usually badly calibrated;
- `pooled` equals `calibration(predicted, actual)` over the same inputs;
- a misaligned pair is refused; empty input is refused by `calibration` itself.

## Does not

Produce forecasts, choose a horizon, or decide whether a model is good enough.
PRD §23.5B and §12's forecast record are separate; promotion belongs to the gate.
