---
id: OUT-2026-10-04-tasks-pass-survives
step: tasks
records: [REQ-INFRA-012]
commit: null
---

## What was done

Eight tasks, then the analysis of `spec.md`, `plan.md` and `tasks.md` against each other. Every FR and SC maps
to a task (the table is in `tasks.md`). The analysis found one thing.

## What was decided

- **SC-001 and SC-002 were missing from the coverage table** although T002 covers them; the rows were added so every FR *and* SC is named, as in the other requirements.

- **FR-007 (the same interval after a failure as after a success) had no task of its own.** T002 now asserts
  the recorded sleeps equal the interval after a failure as well; the plan's test list names it too.
- Checked and consistent: the healthy loop's output is pinned by T004 and the `-- next pass in` line is kept
  exactly; SC-003 (live) is T007 and uses an unreachable object store rather than stopping the real one, so
  nothing the other services use is disturbed.
- **Status goes to `implemented` in the implementing commit**: the live acceptance can be shown today.

## What is still open

- Nothing beyond the plan's list; the live proof is the one thing no unit test can stand in for.
