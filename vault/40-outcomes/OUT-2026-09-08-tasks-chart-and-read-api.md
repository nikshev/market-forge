---
id: OUT-2026-09-08-tasks-chart-and-read-api
step: tasks
records: [REQ-API-001, REQ-WP-009]
commit: null
---

## What was done

15 tasks in six phases, with a coverage table mapping every FR and SC to one.

## What was decided

- **T001 ships the gate before the code it gates.** A CI step added after the
  frontend exists is a step written to pass what is already there.
- **T013's first two mutations are the ones that matter.** Defaulting
  `as_seen_then` to false, or returning a refit when the stored snapshot was
  asked for, both produce a perfectly plausible channel. Every alert this
  system has already sent carries a deep link that would then open a refit, so
  the failure would be retrospective — old signals would start looking better
  than they were, and nothing would say why.

## What is still open

- Nothing from this step.
