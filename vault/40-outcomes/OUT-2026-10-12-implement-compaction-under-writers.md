---
id: OUT-2026-10-12-implement-compaction-under-writers
step: implement
records: [REQ-WP-100]
commit: null
---

## What was done

Diagnosed "the page shows no data" as a read API that took 25 s per request: every container was up and the data was
there, but `bars` had ~3,000 files and maintenance had failed to compact it sixteen passes running (`ValidationException`).
Rewrote `IcebergTable.compact` to replace exactly the files of the snapshot it read, in one commit, with snapshot
isolation set so a concurrent append is not a conflict; the compacted file is ordered as the newest file it replaced,
recorded in a table property keyed by the file's name in the same commit, and the record of a replaced file is removed.

## Evidence

**RED first**: five new tests failed on the old code (the concurrent-writer scenarios and the property bookkeeping). **GREEN**:
the lakehouse suite (149 tests). **On the running table**, from a one-off container with the new code while the daemons kept
writing: 3,019 files / 170,614 rows compacted in 342 s with two commit retries and no failure; the 170,614 rows read before
equal the first 170,614 read after, in order; 38 rows committed meanwhile follow them; the full read went from 16.4 s to
1.3 s; the API's 30-minute bars request from 25 s to 4 s (the host was still loaded: load average 12).

## What was decided / found

- Making the validation permissive alone would have **deleted** the rows committed during the run (the old call replaced the
  table); replacing named files is what makes it safe.
- A compacted file's own sequence number is later than a concurrent writer's, which would invert "latest row wins"; hence the
  recorded order.
- The maintenance container is nine days old and runs the old image: it also reports `dex_swaps: FAILED` (its schema predates
  `ingest_time_ns`). It has to be recreated from the new code.

## Deployed run (2026-10-12, maintenance container rebuilt twice)

- First pass on the new image: `channel_snapshots`, `feature_snapshots`, signals and extrema compacted; **`bars` failed**
  (`CommitFailedException: branch main has changed`) after pyiceberg's default four retries, about a second, against a dozen
  writers. The table is now given forty retries with a 50 ms-2 s backoff (the writers share them).
- Second pass: **every table compacted, no `FAILED`** -- including `dex_swaps`, which the old image could not touch (its schema
  predated `ingest_time_ns`). `bars` took 1,764 s: most of it retries while the daemons kept committing, the table having
  been compacted by hand from 3,019 files an hour earlier and holding 88 by then. A pass is every six hours, so that cost is paid
  in the background and the daemons are not stopped.
- API after: a 30-minute bars request 2.7-3.5 s (it was 25 s), features 2.3 s, with the host's load average still 6-10 and
  swap full (another tenant's `reth`, `minio` at 120-170 % CPU) -- the remaining cost is the host, not the table.

## What is still open

- **Bars lag by up to fifteen minutes by design**: the ingest commits 15 bars at a time (`FLUSH_EVERY_BARS`, [[REQ-WP-068]]) to keep the file count down. With compaction now working under writers the batch could be smaller; that is the owner's call and is not changed here.

- The maintenance container is to be recreated; then its next pass is the evidence for the last acceptance line.
