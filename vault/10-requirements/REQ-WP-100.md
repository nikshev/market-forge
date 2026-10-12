---
id: REQ-WP-100
title: "Compaction lands while writers are writing: a table with many ingest daemons is compacted, and its reads stay fast"
type: work-package
prd_ref: "§36, §29.0; owner's report 2026-10-12 (the page showed no data)"
prd_lines: "6478-6492"
phase: null
status: implemented
depends_on: [REQ-WP-068, REQ-WP-070, REQ-WP-039]
tags: [lakehouse, compaction, concurrency, availability]
hard_gated: false
---

## Requirement

On 2026-10-12 the owner reported that the page showed no data. The services were up and the data was being written; the
**read API answered a thirty-minute bars request in 25 seconds**, because the `bars` table held about three thousand
tiny files and had not been compacted for days. The maintenance log said why, sixteen passes running:
`bars: FAILED -- ValidationException: Added data files were found matching the filter`.

Compaction ([[REQ-WP-068]]) reads every live row, then overwrites the table with one file. That takes minutes on a table
this size, and twelve ingest daemons commit to `bars` every minute, so a writer always committed in between and the
overwrite was refused. (Forced through, it would have deleted that writer's rows, because an overwrite replaces *the
table*, not the files it read.)

This requirement makes compaction **replace exactly the files it read** in one commit that no one else's commit conflicts
with, and keeps the rows' order, which every "latest row wins" reader depends on.

1. Compaction deletes only the data files of the snapshot it read and adds the compacted file(s); a file a writer added
   meanwhile is untouched and stays after it in the order.
2. The compacted file is ordered as the **newest file it replaced**, not by its own (later) sequence number; that is
   recorded against the file in the same commit, and a later compaction removes the record of a file it replaced.
3. The tables are put in snapshot isolation for these operations so a concurrent append is not a conflict; the files it
   deletes are still checked to exist.

## Acceptance

- A compaction during which another writer commits lands, keeps every row once, and returns the number of files it
  compacted (tests).
- The rows come back in the order they were committed -- compacted rows, then the late writer's, then later appends --
  also after a second compaction (tests).
- The per-file order records do not accumulate across passes (test).
- Applied to the running `bars` table (3,019 files, 170,614 rows): it compacts without a failure while the daemons keep
  writing; every row read before is read after, in the same order; the read that took 16 seconds takes about one.
- The maintenance pass reports no `FAILED` for `bars`.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-152-compaction-under-writers]]
- **Code:**
    - `src/channelflow/lakehouse/iceberg.py`
- **Outcomes:** [[OUT-2026-10-12-implement-compaction-under-writers]]
<!-- trace:end -->
