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

## Deployed result (2026-10-13, 11:00-11:08 UTC)

The maintenance container was rebuilt and its first pass over the new compaction took about **seven minutes for every table**: `feature_snapshots`
**38.9 s** (the pass before it, over the same table: 1,612 s), `bars` 141.6 s (42 files), `volume_bins` 47.3 s (12 files), the rest seconds each.

## What is still open

- Nothing in the repository; the next hourly pass will say whether the tail stays small.
