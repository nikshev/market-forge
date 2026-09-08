---
id: OUT-2026-09-08-plan-signal-state-machine
step: plan
records: [REQ-WP-007]
commit: null
---

## What was done

Planned REQ-WP-007 into 13 tasks. Constitution Check passed.

## What was decided

- **The transition table lives alone in `machine.py`**, so "does this skip a
  step" is answerable by reading one file rather than tracing branches.
- **Principle IX matters here for the first time.** PRD §0.11 puts Phases 1 to 3
  under "no automatic execution", and the lifecycle deliberately ends at
  `alerted` rather than at anything actionable.

## What is still open

- Nothing from this step.
