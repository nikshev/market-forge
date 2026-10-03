---
description: "Task list for REQ-WP-079 — a snapshot read resolves its snapshot against the table it reads"
---

# Tasks: A snapshot read resolves its snapshot against the table it reads

**Input**: Design documents from `/specs/124-snapshot-single-load/`

**Tests**: REQUIRED. Every test carries `@pytest.mark.trace("REQ-WP-079")`. Write each test first
and watch it fail **for the stated reason**. Where a test is a guard that passes today by design
(a behaviour the change must not break), the task says so; a RED is never fabricated for it.

**The thread through every test below**: the fault only exists *between* two loads of the table, so
a test that cannot make a commit land between loads cannot see it. That is why the first tasks build
a catalog wrapper that does, and why every behavioural test runs through it. The existing lakehouse
tests are single-process and pass beside the defect.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project: `src/channelflow/`, `tests/`, `tools/` at the repository root. The change is in one
module, `src/channelflow/lakehouse/iceberg.py`.

---

## Phase 1: Setup

- [ ] T001 Record the **before** in the implement outcome note: `PYTHONPATH=. .venv/bin/python specs/124-snapshot-single-load/count_loads.py` (expect 1, 2, 2, 5, 5, 7); on the running stack, the time of `snapshot_ids()`, `read()` and `current()` on `bars` in the `worker` container (planning: 0.21 s, 1.38 s, 4.12 s); and `docker compose logs worker resample | grep -c NoSuchSnapshot` per service with the date (planning: worker 10, resample 4)

## Phase 2: Foundational — a catalog that can make the race happen

- [ ] T002 Write `tests/unit/lakehouse/racing.py` with two wrappers over a real `SqlCatalog`: `CountingCatalog` (counts `load_table` calls per table, exposes the count and a reset) and `RacingCatalog` (**armed explicitly** with `.arm()`, because the test's own set-up appends load tables too: after arming, the first `load_table` of a table is returned clean, and before returning every later one it commits one more row to that table through a second `IcebergTable` handle built on the *unwrapped* inner catalog, so the competing commit neither counts nor races itself). Both delegate every other attribute to the inner catalog. No source change yet
- [ ] T003 [P] Write `tests/unit/lakehouse/test_racing_catalog.py` proving the wrappers do what they say, so a later green is not an artifact of a wrapper that does nothing: the counter counts exactly the loads a call makes; under `RacingCatalog` the second load of a table holds one more snapshot than the first; the first load is untouched; the competing commit goes through the inner catalog (a counter beside it does not move)

## Phase 3: User Story 1 — the newest snapshot comes from one version (P1) 🎯 MVP

**Independent test**: against `RacingCatalog`, 25 consecutive reads of the newest snapshot, of `current()` and of `snapshot(n)` raise no `NoSuchSnapshot`, and `append` returns its own snapshot.

- [ ] T004 [P] [US1] Write the failing test in `tests/unit/lakehouse/test_single_load.py`: over a table with several commits, behind `CountingCatalog`, each public operation loads the table **once** — `snapshot_ids()`, `read()`, `read(snapshot_id=n)`, `current()`, `snapshot(n)`, `append([row])`. Fails today with 1, 2, 2, 5, 5, 7. Parametrised so each operation is its own failing case and its own message
- [ ] T005 [P] [US1] Write the failing test in the same file: behind `RacingCatalog`, 25 consecutive calls of `read()`, `current()` and `snapshot(n)` (with `n` the newest snapshot of the first version) each complete without `NoSuchSnapshot` and return rows of a snapshot that exists in the version they read. Fails today with `NoSuchSnapshot: bars has no snapshot …` — the same message the logs show
- [ ] T006 [P] [US1] Write the failing test in the same file for FR-009: with `pyiceberg`'s `Table.append` patched to commit a competing row through another handle *immediately after* the real append, `IcebergTable.append` returns the snapshot **this call wrote** — its sequence number is the one before the competing commit's, and its record count excludes the competing row. Fails today: the returned snapshot is the competitor's, with no error. This also pins pyiceberg 0.12.0's refresh of `table.metadata` at commit, which the design relies on
- [ ] T007 [US1] Run the three files and record the RED output (command and the failures, enough to show each failed for its stated reason) in the implement outcome note. Do not commit while red: `make validate` runs the suite
- [ ] T008 [US1] In `src/channelflow/lakehouse/iceberg.py`: add `_ids_of(table)`; add `_rows_at(table, snapshot_id)` holding what `read` did after resolving (`_in_commit_order` and the allocation); change `_describe` to take the loaded table and use `_ids_of(table)` and `_rows_at(table, …)` instead of `self.snapshot_ids()` and `self.read(…)`; make `read`, `current`, `snapshot` load once and call only these; make `append` describe `_ids_of(table)[-1]` of the object it appended through; do not call the id list at all on a pinned `read`. Add `# @trace: REQ-WP-079` beside the existing markers. Public signatures and return values unchanged
- [ ] T009 [US1] Make `_allocated`'s `NoSuchSnapshot` message list `_ids_of(table)` of the table it searched, not `self.snapshot_ids()` (a third load, and a list from a different version than the one that failed to contain the number)
- [ ] T010 [US1] Run `tests/unit/lakehouse`, `tests/unit/tables`, `tests/unit/models`, `tests/unit/experiments`, `tests/unit/research` and `tests/unit/pipeline/test_replay*.py` — the callers named in the research — and confirm T004–T006 now pass and nothing else moved. **No existing test is edited** (SC-003): if one needs it, stop and say why, because a test changed to fit the change proves nothing

## Phase 4: User Story 2 — pinned reads stay reproducible and honest (P1)

**Independent test**: a pinned read returns the same rows after later commits; a missing snapshot is refused with the list of the version read; an empty table reads empty.

- [ ] T011 [P] [US2] Write in `tests/unit/lakehouse/test_single_load.py` the **guards that pass today by design**: a pinned read of an existing snapshot returns identical rows before and after later commits (FR-005); a table with no commits reads empty and has no current snapshot (FR-006); `read(snapshot_id=999)` and `snapshot(999)` raise `NoSuchSnapshot` (FR-004). Say in the test's docstring that these are regression guards and were green before the change
- [ ] T012 [P] [US2] Write the one US2 test that **can** fail today, in the same file: behind `RacingCatalog`, a pinned read of a snapshot number the first version does not hold raises `NoSuchSnapshot` whose message lists exactly the snapshot numbers of the version that was read — today it lists those of a later load, so it names snapshots the failing lookup never saw. Fails today for that reason
- [ ] T013 [US2] Run both and record, in the outcome note, which were RED and which were green from the start

## Phase 5: User Story 3 — the fault is gone from the running stack (P2)

- [ ] T014 [P] [US3] Write `tests/integration/test_snapshot_race.py` (marker `integration`, the real-store catalog fixture used by `tests/integration/test_lakehouse_on_minio.py`): a reader looping `read()`, `current()` and `snapshot(n)` beside a writer looping `append`, for a fixed five seconds, with no `NoSuchSnapshot`. Its docstring says it is **evidence and not proof** — it can pass by luck on unfixed code — and points at T005 as the proof

## Phase 6: Mutations, gate, deployment

- [ ] T015 **First**: run `tests/tools/test_mutate.py` — `read_cost.toml` and `dex_tables_iceberg.toml` mutate this same file, and a pattern that no longer matches is an error. Then write `tests/mutations/iceberg_single_load.toml` (tests = `tests/unit/lakehouse`), one mutation per decision: the id list taken from a second load in `read`; the same in `current`; the same in `snapshot`; `append` describing `self.snapshot_ids()[-1]` again; `_allocated`'s message from `self.snapshot_ids()`; the membership check in `snapshot` removed; a pinned read loading the list again. Run `python -m tools.mutate tests/mutations/iceberg_single_load.toml`; **a survivor needs a test that kills it or a written reason**
- [ ] T016 `make lint`, `make typecheck` (the helpers take `_IcebergTable`; `mypy --strict`), `make test`. And FR-007: `git diff --stat` for the change shows **no file under `src/` other than `lakehouse/iceberg.py`**, and `grep -rn "except NoSuchSnapshot" src` finds nothing (it finds nothing today); record both
- [ ] T017 Rebuild and recreate every service that imports the lakehouse (`worker`, `resample`, `api`, `maintenance`, the five `ingest-*`): `docker compose up -d --build`. The same costs as [[REQ-WP-078]]'s recreate apply (up to fifteen buffered bars per ingest process). Then record the **after** of T001: loads per call (expect 1 across the board) and the live timings of `current()` and `read()` on `bars`
- [ ] T018 Write the implement outcome note `vault/40-outcomes/OUT-2026-10-03-implement-snapshot-single-load.md` (before/after, the RED output, which US2 tests were green from the start, mutation survivors and reasons, mistakes). Set the requirement's status to **`tested`**, not `implemented`: the acceptance asks for a full day without `NoSuchSnapshot`, and that has not happened yet. `make graph && make validate`; commit through the gate
- [ ] T019 **After at least 24 hours of the new build running** (SC-002): `docker compose logs worker resample | grep -c NoSuchSnapshot` is **0** in each, and `docker inspect -f '{{.RestartCount}}' channelflow-resample-1` is **0** since the recreate (SC-004), recorded with the date and the container start time in the outcome note. If it is not 0, stop: the single-load reading was not the whole cause, and the plan's R3 is wrong. If it is, set the status to `implemented`, `make graph && make validate`, commit

---

## Coverage

| requirement | task |
|---|---|
| FR-001 newest read from one version | T004, T005, T008 |
| FR-002 `current()` from one version | T004, T005, T008 |
| FR-003 `snapshot(n)` from one version | T004, T005, T008 |
| FR-004 a missing number is refused, by name | T011, T012, T009 |
| FR-005 a pinned read is reproducible | T011 |
| FR-006 an empty table reads empty | T011 |
| FR-007 no caller made to tolerate the error | T016 |
| FR-008 the proof is RED first | T007 |
| FR-009 `append` returns its own snapshot | T006, T008 |
| SC-001 25 reads against a racing catalog | T005 |
| SC-002 a day with zero `NoSuchSnapshot` | T019 |
| SC-003 existing tests unchanged | T010, T011 |
| SC-004 resample does not exit | T019 |

## Dependencies & Execution Order

- T001 first (the before moves once the fix is deployed). T002 → T003; T002 blocks every test task.
- T004, T005, T006 are independent files-in-one-file additions and can be written in parallel;
  T007 follows all three. T008 → T009 → T010.
- US2 (T011, T012) needs T002 and can be written beside US1's tests; it is **not** blocked by T008 in
  the sense of writing, but T013 needs the change in place to report green/red honestly, so run T013
  twice if wanted: before T008 for the RED record, after for the green.
- T014 is independent of T008 for writing and runs after it.
- T015 needs T008; T016 follows T015; T017 follows T016; T018 follows T017; T019 follows T018 by at least a day.

## Parallel opportunities

T003 beside T004–T006; T011, T012 and T014 beside US1's tests.

## Implementation Strategy

**MVP is US1 plus the T015–T018 gate**: it removes the fault and fixes `append`. US2 only guards
what must not change; US3 is the proof on the running stack and is the only task that waits on the
clock. The status stays at `tested` between T018 and T019, on purpose: the requirement says a full
day, and one day is not an hour.
