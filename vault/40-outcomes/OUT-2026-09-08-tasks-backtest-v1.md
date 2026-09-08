---
id: OUT-2026-09-08-tasks-backtest-v1
step: tasks
records: [REQ-WP-010]
commit: null
---

## What was done

10 tasks in four phases: parity, the report, the virtual clock, close-out.

## What was decided

- **T005 asserts an ADR mechanically.** ADR-009 says the report carries no
  economic metric. A test over the report's own field names turns that from a
  decision someone might forget into one they must actively revisit.
- **T008 mutation-checks parity by giving the runner its own transition rule.**
  A parity test that passes when the runner has drifted is worse than none.

## What is still open

- Nothing from this step.
