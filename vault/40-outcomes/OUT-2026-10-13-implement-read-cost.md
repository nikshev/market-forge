---
id: OUT-2026-10-13-implement-read-cost
step: implement
records: [REQ-WP-104]
commit: null
---

## What was done

Specified, planned and implemented [[REQ-WP-104]] (spec 156) in one step; status `tested` until the measurement after the deploy.

- `resample_main.run_pass`: one read of the table, what each target already holds taken from it, every series computed, one append. A failed
  commit is named, writes nothing and is not counted; one series failing does not stop the others.
- `tables.rows.narrow`: an Arrow-side filter (equality, closed/open ranges, `None` = not asked, unknown column = error), used by `read_bars`,
  `feature_points`, the consensus reads and `read_bins`.
- `maintenance_main.TABLES` gains `volume_bins`; a test fails if a `tables/` module declares a table the list does not cover.
  `CHANNELFLOW_MAINTENANCE_INTERVAL` defaults to one hour.

## Evidence

**RED first**: three tests failed on the old resample pass (reads, commits, nothing-to-write) and one on the maintenance list; `narrow` did
not exist. **GREEN**: the same files, the tables/api/lakehouse/deploy/docs suites; lint and type check clean. Mutation sweeps: `resample_pass`
(7 caught, 2 equivalent by design), `tables_narrow` (8 caught).

**Measured on the running stack, before**: bars 54 s, volume profile 82 s, features 5 s, host load average 41, `resample` 345 % CPU, MinIO 250 %.
**After the resample fix alone** (deployed first): load average 12, MinIO 49 %, resample off the CPU list; bars 8.4 s, profile 23.6 s.
**What was left was the files**: `bars` 1,482 files (7.6 s to read), `volume_bins` 5,077 (23.2 s) -- and Python-side conversion was 0.15 s of
it. That is what the maintenance list and the hourly interval address.

## What was decided / found

- The dict conversion was the least of the four causes (about 2 s of the features request); it is fixed because it is free, and the
  measurement says where the rest was: the number of files and the number of reads.
- The compaction commit retries (REQ-WP-100 raised them to 40) turned the resampler's lost commits into a long retry storm while it
  committed per series; one commit per pass removes the contention the retries were absorbing.
- A `.env` value (the local `CHANNELFLOW_MAINTENANCE_INTERVAL=6h`) was changed to `1h` by hand: `.env` is not tracked.

## What is still open

- Whether the API should cache a table read between requests (every chart request re-reads whole tables); not needed once the file counts
  are low, and not done.
