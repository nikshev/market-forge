---
id: OUT-2026-09-08-plan-cross-venue
step: plan
records: [REQ-WP-016]
commit: null
---

## What was done

Four modules under `src/channelflow/crossvenue/`, three test files, 13 tasks.

## What was decided

- **`leadlag` is deliberately absent from the package's exports.** Importing it
  takes a fully qualified module path, which is what makes the import ban
  visible in a diff rather than a matter of intent.
- **The import-ban test asserts its own targets still exist.** Without that
  guard, deleting the signal, alerting or stop package would turn the check
  green — a test that passes because it stopped looking.
- **A window reaching before the data start returns nothing.** A 10-second
  return computed over the 5 seconds that happen to be available is a
  mislabelled number, and mislabelled numbers survive review.
- **"Cannot fill" and "expensive" are different answers**, so an unfillable
  venue is excluded and named rather than ranked last.

## What is still open

- Nothing from this step.
