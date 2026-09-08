---
id: OUT-2026-09-08-plan-channel-baseline
step: plan
records: [REQ-WP-006]
commit: null
---

## What was done

Planned REQ-WP-006 into 14 tasks. Constitution Check passed, with one choice
named rather than assumed.

## What was decided

- **Phase 1 is non-repainting, before the model itself.** The usual order builds
  the thing and then guards it. Here the guard is the product requirement and
  the model is the detail: if the invariant cannot be made to hold, nothing else
  is worth building.
- **`test_no_lookahead.py` is its own file**, so its absence would be obvious.
  A section inside a larger test file can be deleted in a refactor without
  anyone noticing what left.
- **float64 for the fit, stated rather than assumed.** Least squares in log
  space is inherently floating-point; `log` and `exp` are not exact, so using
  `Decimal` would lose precision at the first transcendental call anyway.
  Pretending otherwise would be theatre. Prices arrive as `Decimal` and convert
  once, at a visible boundary.

## What is still open

- Nothing from this step.
