---
id: SPEC-062-calibration-by-horizon
requirement: REQ-WP-023
speckit_path: specs/062-calibration-by-horizon/spec.md
status: draft
---

## Summary

PRD §23.5A conditions all three Target E classes on an explicit horizon.
`calibration()` reports one curve over everything it is handed, and nothing
slices it.

The argument for slicing is the part worth reading. A model's reliability is not
constant across horizons — five bars ahead is nearly the present, fifty is a
different question about a different market. Pooled, a model well calibrated at
short horizons and badly at long ones reports an acceptable number, because the
average is dragged toward whichever horizon supplied the most rows. That is a
fact about the dataset rather than about the model, and the failure it hides is
exactly the one that matters: a forecast is acted on at one horizon, never at
the average of several.

Two decisions follow from that and are worth reading twice.

**A horizon that cannot speak says so.** The point of slicing is to stop an
average speaking for a slice, so a slice with three rows must not report a curve
— it would have borrowed the average's voice in a new place. It reports its count
and the reason instead, and an absent reliability stays distinguishable from a
poor one.

**The pooled figure is kept, beside the slices.** Removing it breaks existing
callers for no gain; replacing the slices with it is the defect this exists to
fix.

## Links

- Requirement: [[REQ-WP-023]]
- The phase it closes: [[REQ-PHASE-7]]
- The models whose probabilities it reports on: [[REQ-WP-018]], [[REQ-WP-019]]
