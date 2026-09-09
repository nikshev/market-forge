---
id: OUT-2026-09-09-plan-bars-table
step: plan
records: [REQ-TBL-001]
commit: null
---

## What was done

A new adapter package, one module, one addition to the plane. 8 tasks.

## What was decided

- **A third package**, because neither side may import the other and both
  prohibitions are already enforced by tests. PRD §29.0 asks for precisely this
  shape.
- **The plane gains a `decimal` type**, stored as exact text. An Arrow decimal
  needs a precision and scale per column that §29's schemas do not give, and
  that would truncate the first value exceeding them.
- **The sink buffers and does not flush on a timer**, because a commit per bar
  would make the metadata larger than the data and because nothing here reads a
  clock.

## What is still open

- Nothing from this step.
