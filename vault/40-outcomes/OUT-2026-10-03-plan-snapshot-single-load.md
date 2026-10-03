---
id: OUT-2026-10-03-plan-snapshot-single-load
step: plan
records: [REQ-WP-079]
commit: null
---

## What was done

Planned the single-load read as `specs/124-snapshot-single-load/` (plan, research, data model,
one contract, quickstart). Planning started from the spec's claim — two loads in `read`, a third in
`snapshot` and `current` — and counted instead of trusting it.

## What was decided

**The count was 2, 5, 5 and 7, not 2 and 3.** A counting wrapper over `Catalog.load_table`
(`specs/124-snapshot-single-load/count_loads.py`) gave `read` 2, `current` 5, `snapshot` 5,
`append` 7, and showed `read(snapshot_id=n)` loads twice for a list it then ignores. The spec
undercounted because it was written from reading `read` alone.

**`append` was in the defect and the spec missed it.** It returns `_describe(snapshot_ids()[-1])`
from a fresh load, so under concurrency it can return another writer's snapshot and raise nothing.
No log would ever have shown that, which makes it the more dangerous half. The spec gained FR-009
and a fourth acceptance scenario; the requirement note's own acceptance is untouched, since a
returned description is a read of a snapshot and the title already covers it.

**The fix is structural, not a retry.** Public operations load once and pass the loaded table to
private helpers (`_ids_of`, `_rows_at`, `_describe`). Rejected, with reasons in the plan: catching
and re-reading (hides the fault, cannot see the `append` half), loading the list before the table
(fixes `read` only and rests on the order of two statements), an in-process cache (five processes,
and invalidation is the same race), a lock.

**`append` relies on a library behaviour, so a test pins it.** pyiceberg 0.12.0 sets
`self.metadata = response.metadata` at the end of `_do_commit`, so the object a writer appended
through already holds its own snapshot as the newest.

**Measured on the live table:** `current()` 4.12 s (4,849 snapshots, 72,806 rows), `read()` 1.38 s,
`snapshot_ids()` 0.21 s. The race window is about four seconds wide, which accounts for fourteen
occurrences in thirteen hours without needing any other explanation.

**SC-001 changed from 1,000 reads to 25.** Each real commit costs ~60 ms and one race already
proves the point; the number the spec first asked for would make the fast gate slow for nothing.

## What is still open

- **`append` spends the whole read time describing itself.** `_describe` reads every row to count
  and hash it, about four seconds on `bars`, on every append. That is a performance requirement of
  its own and probably why writers' commits overlap enough to conflict. Not touched (Principle XII).
- **`compact()` looks able to drop concurrent appends.** It reads the newest rows and overwrites the
  table with them; the read takes seconds while five processes append. Checked against the data:
  no gap in the minute bars around the 21:39 and 03:39 maintenance runs, so it is a risk, not a
  finding. Someone should prove it with a test or dismiss it.
- Whether the pyiceberg refresh behaviour is stable across the next library upgrade; test 3 is
  the alarm.
