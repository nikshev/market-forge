---
id: REQ-WP-068
title: A read of the canonical plane costs what its rows cost, not what its files cost
type: work-package
prd_ref: "§36, §6.4, §45 Phase 8"
prd_lines: "6034-6052, 630-650, 6904-6913"
phase: 8
status: implemented
depends_on: [REQ-WP-067, REQ-WP-066, REQ-WP-039]
tags: []
---

## Requirement

[[REQ-WP-067]] measured §36's `chart historical load p95 < 2s` against a
deployment and found **4.4 seconds at a single client**. The cause is three
compounding defects, each measured, and none of which hides the others.

### The read is serial where it has no reason to be

`IcebergTable.read` orders rows by commit, which [[REQ-WP-039]] made load-bearing:
Iceberg's own scan returns the newest manifest first, and every "latest row wins"
reader in the API folds rows in order. That part is right and stays.

**How it reads them is not.** `_in_commit_order` opens and parses each data file
one after another, so a table of 685 files costs 685 round trips to the object
store in series. Measured on the deployment, same files, same order:

    sequential      4394ms
    16 workers       654ms      6.7x
    32 workers       605ms      7.3x

and the concatenated result is **byte-identical** — order comes from sorting the
paths and concatenating in that order, so only the I/O is concurrent. For
comparison, pyiceberg's own `scan().to_arrow()` takes 1411ms and does not
preserve commit order, which is why it is not the answer.

### The files are one row each

[[REQ-WP-066]]'s daemon commits once a minute and produces one bar a minute, so
every bar became its own file: **685 files holding 689 rows**, each about 8 KiB
of Parquet around a row of a few hundred bytes.

Reading faster does not stop that growing. A day of one symbol at one-minute
bars is 1,440 files; a year is half a million, and the read cost rises with the
count however concurrent it is.

`BarSink`'s docstring states the rule this broke — "a commit per bar would make
the snapshot chain as long as the series" — and `FLUSH_INTERVAL_NS` quotes that
sentence above a value equal to the bar interval.

### An existing table stays broken without being rewritten

The two fixes above are forward-looking. Neither shrinks a table that is already
685 files, and a deployment that ran for a day before them would keep paying for
it until its history expired. pyiceberg 0.12 has no compaction -- its maintenance
surface is `expire_snapshots` alone -- so the plane needs one.

**Measured after adding it**, on the live table of 717 files holding 721 rows:

    compaction                        7.2s, once
    read after                         45ms   (6478ms before)
    chart_historical_load, 16 clients  944ms  (20207ms before), target met

## What measuring found that reasoning did not

The first attempt bounded the read pool **per read**, which made one client
faster and sixteen clients slower -- 20.2s to 29.1s -- because sixteen requests
each opening sixteen files is 256 connections to one object store. The bound has
to be shared across the process, and the load test is what said so.

## Acceptance

- `IcebergTable.read` reads data files concurrently, with a bounded pool, and
  returns rows in exactly the order it returns them today — asserted by equality
  against the serial result, not by inspection.
- The concurrency is bounded and stated, so sixteen concurrent requests do not
  become hundreds of connections to the object store.
- A table of one file is not slower than it is today: the pool is not paid for
  when there is nothing to parallelise.
- The ingest daemon's commits hold more than one bar, and the relationship
  between the flush interval and the bar interval is stated rather than
  coincidental.
- The plane can rewrite a fragmented table into one file, **preserving the
  order `read` guarantees**, asserted by equality against the rows before.
- Compacting a table that needs nothing writes no snapshot.
- Maintenance is a tool that runs deliberately, covering every table a
  deployment appends to — named one by one, because three modules hold more than
  one table and a loop over `table_for` would skip them.
- Measured after all three: §36's chart-load target met at the concurrencies
  [[REQ-WP-067]]'s tool drives, reported by that tool rather than by hand.

## Notes

Neither fix hides the other: the parallel read removes what the current files
cost, and the flush policy stops the count growing. Doing only the first would
pass today and fail again in a month.
