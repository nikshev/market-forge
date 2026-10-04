# Research: pass survives

## R1. Which reads of a pass are unguarded?
`channel_main.run_pass` and `resample_main.run_pass` read the whole `bars` table first
(`bars_table.read_bars(table, …)`), before the per-series loop whose `try/except` prints `FAILED`. An exception
from that read leaves `main`. `maintenance_main` guards each table and is not affected.

## R2. What did the two incidents have in common?
Nothing in cause: `NoSuchSnapshot` (a snapshot race, fixed by REQ-WP-079) and an `OSError` from HTTP 503 on a
`HeadObject` (object store under load). Both were transient and both ended a process. **Decision:** catch
`Exception`, not a list of causes.

## R3. Is repeating a pass safe?
The worker's and the resample's passes are idempotent over unchanged data (their reports count what was
written and what was skipped), so the next pass is a safe retry.

## R4. What do the jobs print today?
`-- next pass in Ns` after every pass, per-series lines inside. **Decision:** keep exactly, add only the failure
and recovery lines.

## R5. How is a loop tested without waiting?
Inject the sleep. **Decision:** `sleep=None` meaning `time.sleep` looked up at call time, so a test patches it
or passes a recorder.
