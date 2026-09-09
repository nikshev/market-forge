---
id: OUT-2026-09-09-spec-corridor-calibration
step: spec
records: [REQ-EXP-009]
commit: null
---

## What was done

`specs/042-corridor-calibration/spec.md`: three user stories, 10 functional
requirements, 10 success criteria.

## What was decided

- **Stability is per fold**, not on average.
- **No winner when nothing holds.**
- **The conformal method sees only past errors**, and the per-instant
  measurements are public so that can be checked.
- **§13.8's levels only.** A target outside 80/90/95 is a different promise, and
  the report would carry it as one of these.

## What is still open

- **The full adaptive conformal scheme.** §13.8 marks it optional; this is the
  rolling residual calibration the same sentence names.
