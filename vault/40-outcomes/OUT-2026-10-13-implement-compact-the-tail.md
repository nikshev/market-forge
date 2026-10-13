---
id: OUT-2026-10-13-implement-compact-the-tail
step: implement
records: [REQ-WP-105]
commit: null
---

## What was done

Specified, planned and implemented [[REQ-WP-105]] (spec 157) in one step; status `tested` until the next maintenance pass is measured.
`IcebergTable.compact(big_rows=BIG_FILE_ROWS)` replaces only the files after the last one of 100,000 rows or more.

## Evidence

**RED first**: six of the seven new tests failed on the whole-table compaction. **GREEN**: the lakehouse suite (170 tests). Mutation sweep over
`read_cost.toml`: 14 caught, 0 survived.

The motivating measurement: the pass over `feature_snapshots` on 2026-10-13 took 1,612 s for 68 small files in front of 1.3 million rows.

## What is still open

- The measurement of the next hourly pass over the features table.
