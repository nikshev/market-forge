---
id: OUT-2026-10-03-implement-snapshot-single-load
step: implement
records: [REQ-WP-079]
commit: c9fdd0c
---

## What was done

Every public operation of `IcebergTable` that names a snapshot now loads the table **once** and
resolves everything against that load: `read`, `current`, `snapshot` and the description `append`
returns. The change is one file, `src/channelflow/lakehouse/iceberg.py` (+33 −12): a static
`_ids_of(table)`, `_describe(table, id)` taking the table it is to describe, the existing
`_in_commit_order` for the rows, and `append` describing from the table object pyiceberg refreshed
at its own commit. No other file under `src/` changed and nothing catches `NoSuchSnapshot`
(FR-007: `git diff --stat` and `grep -rn "except NoSuchSnapshot" src`, both recorded).

**RED, before any source change** (`.venv/bin/python -m pytest tests/unit/lakehouse/test_single_load.py -q`):
`9 failed, 7 passed`.

- `read()` loaded the table 2 times; `read(snapshot_id=2)` 2; `current()` 5; `snapshot(2)` 5;
  `append` 6 (five failures of `assert N == 1`).
- `NoSuchSnapshot: cex_trades has no snapshot 5; it has (1, 2, 3, 4, 5, 6)` out of `read()` under the
  racing catalog — the deployment's own message, reproduced on the first call.
- `append` returned `TableSnapshot(snapshot_id=6, …)` where `5` was this writer's: `assert 6 == (4 + 1)`
  — another writer's snapshot, no error.
- The refusal said `it has (1, 2, 3, 4, 5, 6)` where the version read held `(1, 2, 3, 4)`, for both
  `read` and `snapshot`.

**Green from the start, on purpose** (said in each docstring, no RED fabricated): the one-load count
of `snapshot_ids()`, the pinned read's reproducibility, the empty table, the refusal of a missing
number for `read` and for `snapshot`, and — **a correction to the spec and the plan** — the
race tests for `current()` and `snapshot(newest)`. Planning had said both were exposed to
`NoSuchSnapshot`. They are not: each takes the newest number from the *first* load and looks it up
in later ones, which can only hold more, so they survive by the direction of their mistake. Their
fault was five loads, and that is what the count test catches. Only `read()` raised, which is why
the logs only ever showed `read_bars` as the caller.

**After.** The suite: `3079 passed` (`make test`, services up), including every caller's tests
(`lakehouse`, `tables`, `models`, `experiments`, `research`: 648) with **no existing test edited**.
`make lint`, `make typecheck` clean. Loads per call, same script as the before: `1, 1, 1, 1, 1` and
`append` 2 (the library's own refresh at commit; 1 at `IcebergTable`'s level, which the unit test
asserts).

**Mutation sweep.** `iceberg_single_load.toml`: 8 caught, 0 survived. Each puts back one of the
removed loads or drops a kept check. The two existing specs on the same file still match and pass:
`read_cost.toml` 5 of 5, `dex_tables_iceberg.toml` 1 of 1.

**The integration evidence test measured against the old code.** `tests/integration/test_snapshot_race.py`,
real PostgreSQL catalog and MinIO bucket. With one reader for five seconds it **passed on the old
code 3 runs in 3** — no evidence at all, and a version I nearly committed. With four readers for
eight seconds it failed 3 in 3 with the production message and passes on the fix 2 in 2. The
docstring records both.

**Deployed 2026-10-03 07:18 UTC** (`docker compose up -d --build`; every service recreated).
Live, on `bars` in the `worker` container, before and after: `snapshot_ids()` 0.18 → 0.19 s,
`current()` 4.81 → 3.11 s. `read()` went 1.35 → 0.14 s, **which is not this change**: the recreate
restarted `maintenance`, whose first pass compacted `bars` (291 files), and fewer files read faster.
No claim is made for it.

## What was decided

- **Status `tested`, not `implemented`.** The last acceptance bullet asks for a full day of the
  five-writer stack without `NoSuchSnapshot`, and the new build started at **07:18 UTC on
  2026-10-03**. T019 sets `implemented` after 07:18 on 2026-10-04, with the counts. The log counts
  at the start of that day, for comparison: `worker` 10 and `resample` 5 occurrences,
  `resample` `RestartCount` 1.
- **The evidence test uses four readers**, because one measured as worthless.

## What is still open

- **The 24-hour check (T019).**
- **`append` still reads every row to describe itself** (about three seconds on `bars`), and `current()`
  too. Recorded in the plan as its own piece of work; the single-load change does not touch it.
- **The requirement note's own text says `snapshot()` and `current()` "have the same shape" and are
  exposed.** They have the shape (several loads) but not the exposure. A dated note on the
  requirement says so; its hand-written text is not rewritten.

## Closed afterwards (2026-10-03)

- **`compact()` against a concurrent append: not a risk, shown by experiment.**
  `specs/124-snapshot-single-load/compact_race.py` appends a row between `compact()`'s read and its
  overwrite. pyiceberg detects it: `compact()` **raises `ValidationException`** ("Added data files were
  found matching the filter"), the competitor's row survives (5 rows of 5), and nothing is
  overwritten. `maintenance_main` catches an exception per table ("one table must not end the pass")
  and tries again at the next pass, six hours on. The cost is a skipped compaction, not lost bars; at
  `FLUSH_EVERY_BARS = 15` each writer commits about every fifteen minutes, so a 15-second compaction
  window meets a commit rarely, and the three maintenance runs on record all completed.
- **`append` and `current()` reading every row to describe themselves:** not pursued. It is a cost,
  about three seconds on `bars`, and nothing is wrong because of it; it becomes a requirement when
  something is.
- **The websockets `keepalive ping failed` ERROR traceback and the once-a-bar `BarSink.flush`
  INFO:** left as they are, on purpose. Both are one line or one traceback per event and sit inside
  the log budget of [[REQ-WP-078]].
- **The `copy-trade` plan's `Co-Authored-By: Claude Fable 5` lines:** the user said to ignore them.
