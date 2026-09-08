---
id: OUT-2026-09-08-plan-derivatives
step: plan
records: [REQ-WP-013]
commit: null
---

## What was done

Four modules under `src/channelflow/derivatives/`, four test files, 12 tasks.

## What was decided

- **The z-score helper is shared, written once in `state.py`**, so funding and
  open interest cannot diverge on what "too few observations" means.
- **`state.py` holds the as-of join**, mirroring REQ-WP-017's: the
  point-in-time rule belongs in one place per package rather than in each
  feature function.
- **T008 extends `exposed_feature_names()`.** The registry test compares
  exposed against registered, and the enumeration currently reads only
  REQ-WP-011's package — so a second package could ship unregistered features
  and [[ADR-015]]'s gate would still pass. Extending it is what makes the gate
  about the system rather than about one module.

## What is still open

- Nothing from this step.
