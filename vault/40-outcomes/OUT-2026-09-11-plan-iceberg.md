---
id: OUT-2026-09-11-plan-iceberg
step: plan
records: [REQ-WP-039]
commit: null
---

## What was done

`specs/077-iceberg/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/table.md`, `quickstart.md`. [[REQ-WP-039]] moves to `planned`.

## The open question, measured rather than guessed

The spec asked whether a point-in-time read uses Iceberg's snapshot lookup or a
row filter over event time. The measurement used a second commit that
**backfills earlier rows**, which is what this system's replays produce:

    commit 1: event times 100, 200
    commit 2: event times  10,  20

    by snapshot 1   -> 100, 200
    by filter <=200 -> 10, 20, 100, 200

Neither alone. The snapshot is the knowledge dimension; the filter is the
market-time dimension; PRD Principle I names both in one sentence — "data with
`event_time <= t` that was actually available then". The hand-rolled `read`
already composes them, and the composition carries over as
`scan(snapshot_id=..., row_filter=...)`.

Worth noting that either answer alone looks right in isolation and fails only on
a backfill. This is the third measurement in two days that settled something a
plausible argument had got wrong, and the first one that was measured *before*
it reached a document.

## What was decided

- **Snapshot ids stay small sequential integers.** Iceberg allocates 64-bit
  ids; callers use `1, 2, 3`. The table maps between them by commit order so
  FR-010 holds and no domain code learns what Iceberg is.
- **[[ADR-053]]'s hash is recomputed over rows, and the values change.** The old
  hash digested per-file digests; this one digests rows. The rule is preserved,
  the numbers are not, and saying so here is cheaper than someone discovering it
  by comparing two vaults.
- **`unreferenced_files()` lives in this module**, not in retention. It is
  knowledge about Iceberg's layout, and retention should need none.

## What is still open

- **Callers have not moved**, and the old format is still here. A half-migrated
  plane is a state to leave quickly.
- **Where the catalog lives on the stack**, and who creates the namespace.
