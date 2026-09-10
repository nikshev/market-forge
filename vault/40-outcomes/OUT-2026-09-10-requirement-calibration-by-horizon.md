---
id: OUT-2026-09-10-requirement-calibration-by-horizon
step: requirement
records: [REQ-WP-023]
commit: null
---

## What was done

[[REQ-WP-023]] extracted from PRD §23.5A and §45's Phase 7. It is the last entry
in [[REQ-PHASE-7]]'s `not_delivered`.

## What was decided

- **The requirement is written around why the aggregate is wrong, not around
  the missing feature.** `calibration()` exists and reports one curve. Slicing it
  is easy; the argument for slicing is the part worth writing down — a model well
  calibrated at short horizons and badly at long ones reports an acceptable
  average, dragged toward whichever horizon has the most rows. That is a fact
  about the dataset, not about the model, and the failure it hides is the one
  that matters, because a forecast is acted on at one horizon rather than at the
  average of several.
- **A thin horizon is unmeasured, not poorly calibrated.** The whole point of
  slicing is to stop an average speaking for a slice; a slice that cannot speak
  must say so rather than borrow the average's voice. This is the one derived
  piece, and the derivation is in the note.
- **The horizon comes from the row's own label.** `Label.horizon_end_ns` minus
  `as_of_ns` is already there, and a horizon supplied alongside the predictions
  is one a caller can get wrong without anything noticing.
- **A pooled figure is reported beside its slices, never instead.** Removing it
  would break existing callers for no gain; replacing the slices with it is the
  defect.

## What is still open

- **Producing the forecasts is out of scope.** §23.5B's time-and-price regression
  and §12's forecast record are separate work; this is about how an existing
  probability is reported.
- **What counts as "too few observations" is a threshold**, and PRD §23.8 does
  not give one. Whatever is chosen will be arbitrary at the margin and must be
  the caller's to set rather than a constant buried in the reporter — Principle X.
