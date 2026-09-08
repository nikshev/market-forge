---
id: OUT-2026-09-08-plan-bar-aggregation
step: plan
records: [REQ-WP-005]
commit: null
---

## What was done

Planned REQ-WP-005 into 13 tasks. Constitution Check passed.

## What was decided

- **Two properties here are absences, not features.** The builder takes no clock
  argument and imports no time module, so wall-clock cannot influence a boundary
  even by accident. And a finalized bar is popped and forgotten, so there is
  nothing left to amend. An absence is easier to verify than a convention.
- **SC-006 is asserted over the source.** "The builder does not use wall-clock
  time" is the kind of property that holds until someone adds a convenience, so
  a test reads the module and fails if a clock appears.

## What is still open

- Nothing from this step.
