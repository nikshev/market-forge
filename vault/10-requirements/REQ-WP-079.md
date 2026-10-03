---
id: REQ-WP-079
title: A snapshot read resolves its snapshot against the table it reads
type: work-package
prd_ref: "§6.4, §7"
prd_lines: "600-642, 786"
phase: null
status: planned
depends_on: [REQ-WP-039]
tags: [lakehouse, reliability]
hard_gated: false
---

## Requirement

PRD §6.4 puts the normalized, feature and research datasets in Iceberg tables "where snapshot
isolation, schema evolution, partition evolution and reproducibility matter". A read of the
newest snapshot of a table must therefore see one table: the snapshot it names and the rows it
returns come from the same version of that table's metadata, however many writers commit while
it runs.

On 2026-10-03, the morning after [[REQ-WP-078]] closed, the deployment's own logs showed that this
does not hold. `IcebergTable.read` loads the table (`self._table()`), then asks `snapshot_ids()`
for the newest snapshot — which loads it **again** — and resolves that number against the
**first** load. Five ingest processes and the resample job commit to the `bars` table; when a
commit lands between the two loads, the number names a snapshot the first load has never heard
of, and `_allocated` raises `NoSuchSnapshot`:

| where | what the log says | effect |
|---|---|---|
| `worker` | 10 × `FAILED — NoSuchSnapshot: bars has no snapshot …`, first at 16:27 on 2026-10-02 | that series is not refitted for the pass; the next pass retries |
| `resample` | 3 × the same, caught per series, and 1 × uncaught at 01:02 on 2026-10-03 (`run_pass`'s first read, outside the per-series handler) | a series is skipped for a pass; once the process exited and compose restarted it |

`snapshot()` and `current()` have the same shape — `snapshot_ids()` then `_describe()`, which
loads the table a third time — and have not yet been seen to fail only because nothing in the
deployment calls them while writers are active.

This is not a rare event: it is the expected result of the design wherever two processes use one
table, and it grows with the number of writers.

## Acceptance

- `read()` of the newest snapshot, `current()` and `snapshot(n)` each resolve against **one**
  load of the table. Proven deterministically with a catalog whose successive loads of a table
  return successive versions: the test fails today with `NoSuchSnapshot` and passes once the
  operation uses a single load.
- A read pinned to a snapshot that genuinely does not exist still raises `NoSuchSnapshot` naming
  the snapshots that do — the fix must not turn a missing snapshot into an empty or newer one.
- A read pinned to an existing snapshot returns the same rows before and after later commits
  (reproducibility, PRD §0 item 13), unchanged by the fix.
- A reader running in a loop beside a writer committing in a loop over a real catalog completes
  without `NoSuchSnapshot`. This is evidence, not proof: the deterministic test above is the proof.
- After deployment, the `worker` and `resample` logs hold no `NoSuchSnapshot` over a full day
  of five-writer operation, recorded with the date.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-124-snapshot-single-load]]
- **Outcomes:** [[OUT-2026-10-03-plan-snapshot-single-load]], [[OUT-2026-10-03-spec-snapshot-single-load]], [[OUT-2026-10-03-tasks-snapshot-single-load]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
