---
id: OUT-2026-09-09-plan-corridor-calibration
step: plan
records: [REQ-EXP-009]
commit: null
---

## What was done

One module, one snapshot field set by four baselines, 8 tasks.

## What was decided

- **The raw slope became a snapshot field**, closing the gap [[ADR-049]] named:
  PRD §13.7's forecast centre needs it and `slope_normalized` cannot serve.
- **The quantile fitter's slope is converted back to per-bar.** It fits on a
  centred, scaled index, and reported as-is its slope was eighteen times too
  small — which the first run showed as a flat 0.00000 beside three baselines
  agreeing on 0.002.

## What is still open

- Nothing from this step.
