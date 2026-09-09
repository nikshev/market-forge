---
id: OUT-2026-09-09-plan-outcomes-economics
step: plan
records: [REQ-BT-001]
commit: null
---

## What was done

Three modules and 11 tasks.

## What was decided

- **Three modules, not one.** An outcome is a fact about price, a fill is a fact
  about execution, and the metrics are arithmetic over both — and only the third
  may require a cost model. Merged, §41 rule 9's gate would stand in front of a
  resolution that does not need it.
- **The signal-quality report is untouched**, so a reader holding one is never
  holding a gross figure that looks like a net one.
- **`statistics` rather than NumPy** for the dispersion measures: the inputs are
  lists of a few dozen floats, and the standard library says what it computes.

## What is still open

- Nothing from this step.
