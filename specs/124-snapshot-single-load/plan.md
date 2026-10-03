# Implementation Plan: A snapshot read resolves its snapshot against the table it reads

**Branch**: `124-snapshot-single-load` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/124-snapshot-single-load/spec.md`

## Summary

Every public operation that names a snapshot — reading the newest, describing the current one,
describing one by number, and the description `append` returns — asks the catalog for the table
several times and combines the answers. Each answer is a different version when another process
commits in between. The plan makes each operation **load the table once and pass that loaded
table to every step after it**, so the snapshot a step names and the metadata it is resolved
against cannot disagree. Nothing is retried, caught or cached.

Planning also found that the spec undercounted. The spec said two loads for `read` and a third for
`snapshot`/`current`; the count is **2, 5, 5 and 7**, and `append` returns a description of
"whatever is newest after my commit", which under concurrency can be **another writer's snapshot**
with no error at all. That is the same defect in a form no log would show, so it is in scope
(FR-009, added to the spec).

## What planning measured

**Loads of the table per call**, on a SQLite catalog with a counting wrapper
(`count_loads.py` beside this plan, run before any change):

| operation | loads today | target |
|---|---|---|
| `snapshot_ids()` | 1 | 1 |
| `read()` | 2 | 1 |
| `read(snapshot_id=2)` | 2 | 1 |
| `current()` | 5 | 1 |
| `snapshot(2)` | 5 | 1 |
| `append([row])` | 7 (6 in the unit test) | 1 |

The planning script patches the shared catalog object, so it also counts pyiceberg's own refresh at
commit; the unit test counts only the loads `IcebergTable` makes. Hence 7 and 6, and after the change
2 and 1.

`read(snapshot_id=2)` loads twice although it does not need the list: `snapshot_ids()` is called
before the branch that ignores it.

**The window is wide.** On the live `bars` table (4,849 snapshots, 72,806 rows), `snapshot_ids()` is
0.21 s, `read()` 1.38 s and `current()` **4.12 s**. A race whose window is four seconds wide, with five
writers each committing once a minute, is not a rare one — which matches fourteen occurrences in
thirteen hours.

**`append` pays the same four seconds.** It ends with `_describe(snapshot_ids()[-1])`, which reads
the whole table to count and hash it. That is a performance finding, not this change (Principle
XII: correctness first). It is recorded as open, because it is also why a writer holds its commit
open long enough for the others to conflict.

**pyiceberg 0.12.0 refreshes the table object at its own commit** (`Table._do_commit` sets
`self.metadata = response.metadata`). So after `table.append(...)` the same object's newest snapshot
**is the one this writer committed**, and describing it needs no second load. This is a property of a
library version, so a test pins it (below) rather than a comment trusting it.

**Audit of every load site in `lakehouse/iceberg.py`**: `read`, `snapshot_ids`, `snapshot`,
`current`, `append` (via `_describe`), `_describe`, `_allocated`'s error message — changed.
`delete_older_than`, `prune_metadata`, `compact`, `expire_snapshots_*`, `unreferenced_files`,
`handle`, `_require_table` — each loads once and uses that one table; left alone.

**One risk seen, not a finding.** `compact()` reads the newest rows and then `overwrite`s the table
with them; the read takes seconds while five processes append. If an append lands between, the
overwrite looks able to drop it. The bars table was checked: no gap in the minute bars around the
maintenance runs at 21:39 and 03:39, so nothing says it happens. It is not this change and is
recorded in the outcome note for someone to prove or dismiss.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict` over `src/`

**Primary Dependencies**: pyiceberg 0.12.0 (`SqlCatalog`), pyarrow

**Storage**: Iceberg tables over PostgreSQL catalog + MinIO in the stack; SQLite catalog in tests

**Testing**: pytest; a catalog wrapper that counts loads, and one that commits between loads

**Target Platform**: the `worker`, `resample`, `api`, `ingest-*` and `maintenance` containers, all of
which import `channelflow.lakehouse`

**Project Type**: library layer under every service

**Performance Goals**: none stated; fewer loads is a consequence, measured before and after

**Constraints**: public signatures and return values unchanged; `NoSuchSnapshot`'s message unchanged

**Scale/Scope**: one module, `src/channelflow/lakehouse/iceberg.py`

## Constitution Check

| Principle | Result |
|---|---|
| I. No look-ahead | **Holds.** One load can only return a version that existed; a result a moment old is what an earlier reader got. |
| III. History is immutable | **Holds.** Nothing is written differently; only the order of reads changes. |
| VII. Live and replay are the same code | **Holds, and is the reason to fix it here.** The worker's replay and the API's reads share this layer. |
| XI. Results are reproducible | **Holds, with a test.** Pinned reads return identical rows after later commits (FR-005). |
| XII. Correctness precedes performance | **Holds.** The speed-up is a side effect; the one expensive step (`_describe` reading everything) is left alone. |
| XIV. Everything is traceable | Tests marked `REQ-WP-079`; the changed file carries the marker. |

Re-checked after design: no violations; Complexity Tracking is empty.

## Approach and what was rejected

**Chosen — thread the loaded table through private helpers.** A pure `_ids_of(table)`; `_describe(table,
snapshot_id)`; and the existing `_in_commit_order(table, id)` for the rows (what `read` did after
resolving, so no new function was needed -- the plan first named a `_rows_at`); public operations
load once and call these. `append` describes from the table object
pyiceberg refreshed at its commit.

**Rejected — catch `NoSuchSnapshot` and read again** (in callers, or inside `read`). It hides the
fault behind a loop, leaves the 5- and 7-load operations as they were, and cannot see `append`
returning the wrong snapshot because that raises nothing. FR-007 forbids it for callers; inside
`read` it fails for the same reasons.

**Rejected — load the list first, then the table.** Reversing the two loads in `read` does fix
`NoSuchSnapshot` (the later load can only have more snapshots) and is a two-line change. It leaves
`current` and `snapshot` at 5 loads each, `append` unfixed, and keeps a correctness property resting
on the *order* of two lines that nothing tests.

**Rejected — cache the table in the process.** The five writers are five processes; a cache needs
invalidation, and invalidation is the same race.

**Rejected — move the whole read into a transaction or lock.** Iceberg has no read lock; an
advisory lock in Postgres would serialise the readers against the writers for the four-second
window.

## Tests (written first)

1. **Load counts** — a catalog wrapper counts `load_table`; each public operation, over a table
   with several commits, loads once. Fails today with 2, 5, 5, 7. The structural guard: a second
   `self._table()` added later fails it.
2. **A commit lands between loads** — a wrapper that commits one more row through another handle
   *before returning each load after the first*, so the race happens on every call, not once an hour.
   Over 25 consecutive reads of the newest snapshot, `current()` and `snapshot(n)`, no
   `NoSuchSnapshot`. Fails today. (`append` is not raced this way: its first load is the clean one,
   so it is covered by test 3, which commits the competitor *after* the writer's own commit.)
3. **`append` returns its own snapshot** — a competing commit lands immediately after this writer's;
   the returned snapshot is this writer's number and content. Pins the pyiceberg refresh.
4. **A missing snapshot is still refused, by name** — and the message lists the snapshots of the
   version read.
5. **A pinned read is reproducible** — rows identical before and after later commits.
6. **A table with no commits** reads empty and has no current snapshot.
7. **Evidence, not proof** — a reader looping beside a writer looping over a real catalog, no
   `NoSuchSnapshot`. In `tests/integration`, because it is probabilistic.

A mutation spec for `iceberg.py`'s new helpers follows: the second load put back in each of the
five operations, the membership check removed, the error's id list taken from another load.

## Project Structure

```text
specs/124-snapshot-single-load/
├── plan.md  research.md  data-model.md  quickstart.md  tasks.md (not yet)
└── contracts/lakehouse-read.md

src/channelflow/lakehouse/iceberg.py           # the change
tests/unit/lakehouse/test_single_load.py       # tests 1-6
tests/integration/test_snapshot_race.py        # test 7
tests/mutations/iceberg_single_load.toml
```

**Structure Decision**: one module, one new unit test file, one integration test; no new package.

## Deployment

Every service imports this layer, so every image that carries it is rebuilt. The log cap and
restart effects of a recreate are those [[REQ-WP-078]] recorded (up to fifteen buffered bars per
ingest process). The check is the day's log: `grep -c NoSuchSnapshot` over `worker` and `resample`.

## Complexity Tracking

Empty: no constitution violation to justify.
