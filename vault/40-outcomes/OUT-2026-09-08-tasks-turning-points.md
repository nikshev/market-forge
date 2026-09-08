---
id: OUT-2026-09-08-tasks-turning-points
step: tasks
records: [REQ-WP-019, REQ-NRT-A, REQ-NRT-B, REQ-NRT-C, REQ-NRT-D, REQ-NRT-E]
commit: null
---

## What was done

17 tasks in five phases, with a coverage table mapping every FR and SC to one.

## What was decided

- **T008 is the task to get right.** A future-bar invariance test comparing two
  empty lists passes. So does one comparing only the count, or only the last
  record. It appends random bars, asserts the prior outputs are non-empty
  first, and compares every field of every one.
- **T016 is a task, not a step.** Setting REQ-WP-019 to `tested` rather than
  `implemented` is a judgement ([[ADR-023]]) and the tooling will not make it:
  no validator rule reads acceptance criteria, so nothing would object to
  marking it implemented.

## What is still open

- Nothing from this step.
