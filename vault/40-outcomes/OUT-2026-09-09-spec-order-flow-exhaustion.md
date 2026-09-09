---
id: OUT-2026-09-09-spec-order-flow-exhaustion
step: spec
records: [REQ-EXP-014]
commit: null
---

## What was done

`specs/047-order-flow-exhaustion/spec.md`: three user stories, 14 functional
requirements, 15 success criteria.

## What was decided

- **Two separate computations**, not one with a retrospective flag. The arms
  differ in their window, in what they may read, and in what their number means.
- **The conditional arm declares itself retrospective in a field**, because that
  is the thing a reader has to carry away from the number.
- **The predictive arm's calling threshold is part of the look-ahead rule**, not
  a detail beside it.
- **The report names which of four cases each signal is in**, and lists the ones
  that explain without forecasting.

## What is still open

- **The signals and the extrema are supplied.** Computing either here would make
  this a test of the feature registry and the detector rather than of EXP-014's
  question.
