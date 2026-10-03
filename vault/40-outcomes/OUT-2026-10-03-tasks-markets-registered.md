---
id: OUT-2026-10-03-tasks-markets-registered
step: tasks
records: [REQ-WP-081]
commit: null
---

## What was done

Broke the plan into 12 tasks, then ran the analysis of `spec.md`, `plan.md` and `tasks.md` against each
other. Every FR and SC maps to a task (the table is in `tasks.md`). The analysis found one thing.

## What was decided

**The analysis found, and what was done:**

- **FR-006's "must not be retried in a loop" had no test.** The spec and the plan both say registration is
  tried once and its failure is a warning; the first draft of T003 asserted the warning and that ingest
  runs, which a retry loop with a sleep would also satisfy. T003 now asserts registration is **attempted
  once**.

Checked and found consistent: the five-threads case is in T003 (SQLite) and T008 (PostgreSQL); SC-003
(bars unchanged when registration fails) is carried by `run` still being called through `main`, since the
bars path is exactly what `run` is; the spec's "a key held with trading rules is not overwritten" is in T003.

**Also decided.** The status goes to `implemented` in the implementing commit, not `tested`: unlike the
Mini App and the snapshot work, this requirement's live acceptance (five rows on the running stack) can be
shown today, in T011, without anything only the owner holds.

## What is still open

- Whether the SQLite thread test is stable enough for the fast gate (T003 finds out; T008 is the fallback).
