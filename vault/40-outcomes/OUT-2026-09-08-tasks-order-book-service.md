---
id: OUT-2026-09-08-tasks-order-book-service
step: tasks
records: [REQ-WP-004]
commit: null
---

## What was done

12 tasks in six phases, with a coverage table mapping every FR and SC to one.

## What was decided

- **Phase 0 is the move, alone.** A relocation mixed into a feature commit makes
  every later failure ambiguous between "the new code is wrong" and "the import
  moved".
- **FR-003 gets a test task and no implementation task.** Exact sequence
  validation already exists from REQ-WP-003. It stays in the list because it is
  still this feature's guarantee, and T010 mutation-checks it rather than
  trusting inheritance.
- **T010 targets the three refusals specifically.** Two of this feature's three
  central guards are refusals, and a refusal that stops refusing looks exactly
  like a green suite. The backtest work hit that shape twice.

## What is still open

- Nothing from this step.
