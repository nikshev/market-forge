---
id: OUT-2026-09-09-plan-training-gate
step: plan
records: [REQ-US-007]
commit: null
---

## What was done

One module, three changed signatures, every caller updated. 9 tasks.

## What was decided

- **The certificate lives with the dataset, not with the models.** It is a
  statement about data; beside the estimators it would be a modelling concern a
  new estimator could forget.
- **The signature test reads `inspect.signature`**, so a fifth training entry
  point fails it by existing rather than by being remembered.
- **A `certified` fixture in the tests**, rather than a stub. A test's dataset
  is now checked the way a caller's is, so a fixture with a leak in it fails
  loudly instead of quietly training something.

## What is still open

- Nothing from this step.
