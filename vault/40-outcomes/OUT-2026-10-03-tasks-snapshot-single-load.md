---
id: OUT-2026-10-03-tasks-snapshot-single-load
step: tasks
records: [REQ-WP-079]
commit: null
---

## What was done

Broke the plan into 19 tasks in six phases (setup, a racing catalog, US1, US2, US3, then mutations,
gate and deployment), then ran the analysis of `spec.md`, `plan.md` and `tasks.md` against each
other. It found five things; each was fixed in the artifacts before this commit.

## What was decided

**The analysis found, and what was done:**

- **FR-007 and SC-004 had no task.** The spec forbids making callers tolerate `NoSuchSnapshot`, and
  asks that `resample` stop exiting; the tasks tested neither. FR-007 became a check in T016 (the
  diff touches no file under `src/` but `lakehouse/iceberg.py`, and nothing catches the error —
  today nothing does). SC-004 became `RestartCount` of `resample` in T019.
- **The tasks never named the requirement they covered.** A coverage table now maps every FR and SC
  to a task; the first pass left FR-001..003, FR-007, FR-008, SC-001, SC-003 and SC-004 unreferenced
  by id.
- **The plan said `append` is raced by the wrapper; it is not.** The racing catalog returns the
  *first* load clean, and `append` loads once, so it never sees a race there. Its test (T006) commits
  the competitor *after* the writer's own commit instead. The plan's wording is corrected.
- **"After the first load" was ambiguous.** A test's own set-up appends load tables too, so the
  wrapper is armed explicitly and "first" means the first load after arming (T002).
- **SC-003 ("existing tests unchanged") had no guard.** T010 now says that editing an existing test
  stops the work, because a test changed to fit the change proves nothing.

**Status stays `tested` until a day has passed.** The requirement's last acceptance bullet asks for
a full day without `NoSuchSnapshot` on the running stack, which no amount of testing can bring
forward. T018 sets `tested` and T019, at least 24 hours after the new build starts, sets
`implemented`. The alternative — `implemented` on the day, with the evidence promised for later —
is how REQ-WP-076 was marked done and then found not to work.

**US2's guards are not given a fabricated RED.** Four of its five tests pass today by design; only
T012 (the message lists the version actually read) can fail now, and it is the one that was read
against the code to be sure it does (`_allocated` builds the message from `self.snapshot_ids()`, a
separate load).

## What is still open

- Whether `RacingCatalog`'s competing commit (a full append through a second handle) makes the unit
  test slow enough to matter in the fast gate; measured at ~60 ms an append, so 25 × 3 operations
  should be a few seconds, to be confirmed at T007.
- `_describe` reading every row to hash it is untouched and still costs seconds per `append`; the
  plan records it as its own requirement's work.
