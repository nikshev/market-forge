---
description: "Task list for REQ-NRT-UPSAMPLE — no unfinalized higher-timeframe close reaches a lower-timeframe consumer"
---

# Tasks: No unfinalized higher-timeframe close reaches a lower-timeframe consumer

**Input**: Design documents from `/specs/125-no-unfinalized-upsample/`

**Tests**: REQUIRED, and **already written**: `specs/125-no-unfinalized-upsample/red/test_upsample_seam.py`
(11 tests, every one marked `@pytest.mark.trace("REQ-NRT-UPSAMPLE")`), with its RED run in
`red/red_run.txt` — `4 failed, 7 passed` against the unchanged code. They sit outside `tests/` because
a red suite cannot be committed; T002 moves them in, and the commit that does so is the one that makes
them green. Seven of the eleven are guards that pass today by design and say so in their docstrings.

**Why the rung is skipped here**: the requirement is `hard_gated`. R5 forbids a status past
`specified` without a linked test in the repository, and a test cannot be linked while it is red, so
`status` stays `specified` until T012 and then goes to `tested` and `implemented` together.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project: `src/channelflow/`, `tests/`, `tools/` at the repository root.

---

## Phase 1: Setup

- [ ] T001 Record the **before** in the implement outcome note: `PYTHONPATH=. .venv/bin/python specs/125-no-unfinalized-upsample/probe.py` (expect bars=1 for the repeated-minute and non-final windows); the live count of duplicate one-minute keys (planning: 55,546 rows, 55,546 keys); and the resample container's refused lines (`docker compose logs --since 1h resample | grep -c "refused:"`) with the date, so the "after" can be compared

## Phase 2: Foundational

- [ ] T002 Copy `specs/125-no-unfinalized-upsample/red/test_upsample_seam.py` to `tests/unit/test_upsample_seam.py` **verbatim** — no edit that would make a red test green. Run it, confirm `4 failed, 7 passed` for the stated reasons, and paste the run's output into the implement outcome note. Do not commit while red

## Phase 3: User Story 1 — a window is a bar only if every minute is there, once, and final (P1) 🎯 MVP

**Independent test**: the five window shapes yield exactly one bar and exactly three refusals; each refusal names the window and what was wrong.

- [ ] T003 [US1] In `src/channelflow/pipeline/resample.py` replace `len(window) != expected` with the identification of `contracts/resample-seam.md` and `data-model.md`: build the expected set of source open times for the window, count held bars per open time, and compute `missing`, `duplicated` and `not final`; any non-empty refuses the window. `Refusal.present` becomes the number of **distinct** expected minutes held; `reason` keeps its existing prefix (`window <s> at <T> has <n> of <m> source <S> bars`) and appends `; missing [..]`, `; duplicated [..]`, `; not final [..]` with open times for whichever apply. Signature unchanged. Add `# @trace: REQ-NRT-UPSAMPLE` beside the module's other marker
- [ ] T004 [US1] Run `tests/unit/test_resample.py`, `tests/unit/pipeline/test_resample_main.py` and `tests/unit/test_upsample_seam.py`: the existing tests pass **unchanged** (no existing test edited) and the four RED tests are green
- [ ] T005 [US1] **A differential check on real data, recorded**: read every one-minute row of the live `bars` table in the `worker` container (as in the WP-079 measurements), run the **old** `resample` (`git show HEAD:src/channelflow/pipeline/resample.py` loaded under another name) and the **new** one per `(venue, symbol)` and target timeframe with the same `now_ns`, and compare. Expect identical bars and identical refusal counts, because the data holds no duplicate and no non-final bar. A difference is a finding: stop and say so

## Phase 4: User Story 2 — nothing inside an open window can be read (P1)

**Independent test**: a resampled five-minute bar written to a real table is absent as of seven instants inside its window and present as of its close.

- [ ] T006 [US2] Confirm the two US2 tests in `tests/unit/test_upsample_seam.py` are green and say in the outcome note that they were green **before** the change by design — the as-of read already filtered on `close_time_ns`; what was missing was a test that asked. No source change belongs to this story

## Phase 5: User Story 3 — a read as of `t` never holds a bar that closes after `t` (P1)

**Independent test**: over a day of source bars stored at every configured timeframe, no read as of any chosen `t` returns a bar with `close_time_ns > t`; a read ignoring `as_of_ns` does.

- [ ] T007 [US3] Bring `tests/unit/test_upsample_seam.py` under **60 seconds** (SC-004; it took 160 s): store the day's fixture **once** per module (a module-scoped fixture, not a call in each test), and measure what the instants cost before choosing how many. The instants must still include the instant before, at and after every window boundary of every configured timeframe up to a day, which is where a leak would show. If the budget cannot be met without dropping those, **change SC-004 in the spec with the reason** rather than thinning the test silently. Record the before and after times
- [ ] T008 [US3] Confirm the control test (a read that ignores `as_of_ns` does meet future bars) still fails if the as-of argument is removed from the property test — by running it once with that argument deleted, then restoring it

## Phase 6: User Story 4 — a leaking resampler is caught, and named (P2)

**Independent test**: each deliberately leaking resampler is reported by the mutation sweep as caught, by name.

- [ ] T009 First run `tests/tools/test_mutate.py`. Then write `tests/mutations/resample_leak.toml` (source `src/channelflow/pipeline/resample.py`; tests `tests/unit/test_upsample_seam.py` and `tests/unit/test_resample.py`) with one mutation per leak, each an exact-once anchor in the **new** code: the window in progress is emitted (`if close > now_ns: continue` removed); the completeness check removed entirely; identification replaced by a count; finality ignored; duplicates ignored; missing minutes ignored. Run `python -m tools.mutate tests/mutations/resample_leak.toml`; **a survivor needs a test that kills it or a written reason**
- [ ] T010 [US4] Write `tests/mutations/bars_as_of.toml` (source `src/channelflow/tables/bars.py`; tests `tests/unit/test_upsample_seam.py` and `tests/unit/tables`) with the table-side leak: `event_time_column="close_time_ns"` changed to `"open_time_ns"` — which would return every in-progress window to every as-of reader. Run it; a survivor is not acceptable here: it would mean the seam's own storage filter is untested
- [ ] T011 [US4] Record the sweeps' totals and the name of each mutation caught in the outcome note; this is the evidence for the requirement's "caught by the suite and **named**, proven by introducing one"

## Phase 7: Gate and close

- [ ] T012 `make lint`, `make typecheck`, `make test` (the suite runs with no services for this requirement: confirm `tests/unit/test_upsample_seam.py` passes with the stack stopped, or say which test it used a service for). Write the implement outcome note, set the requirement to `tested` **and** `implemented` in the one commit (the rung is passed through; the RED run is the proof), `make graph && make validate`, commit through the gate naming explicit paths
- [ ] T013 **Deployment is deferred, on purpose**: the shared image rebuild recreates every service, including `resample` and `worker`, which would restart the 24-hour clock [[REQ-WP-079]] is being measured on (07:18 UTC 2026-10-03 to 2026-10-04) and reset the `RestartCount` it asks for. Deploy after that check, then confirm the resample log's `refused:` lines are unchanged in number against T001's. Not a precondition for this requirement's acceptance, which asks for a suite with no services and no network

---

## Coverage

| requirement | task |
|---|---|
| FR-001 exactly once and final | T003, T004 |
| FR-002 refusal names the window and what was wrong | T003, T004 |
| FR-003 an open window yields nothing | T004 (kept, green) |
| FR-004 nothing readable inside a window | T006 |
| FR-005 no bar closing after `t` | T007, T008 |
| FR-006 each leak caught, by name | T009, T010, T011 |
| FR-007 no services, no network | T012 |
| FR-008 the proof is RED first | T002 |
| SC-001 one bar, three refusals | T004 |
| SC-002 zero late bars at every `t` | T007 |
| SC-003 four leaks caught, none surviving unexplained | T009, T010 |
| SC-004 under a minute | T007 |

## Dependencies & Execution Order

T001 first. T002 → T003 → T004 → T005. T006–T008 need T002 (they are tests already written) and run
after T004 so the suite is green together. T009 needs T003 (anchors are the new code); T010 is
independent of T009. T012 follows everything; T013 follows T012 by however long the WP-079 check takes.

## Parallel opportunities

T010 beside T009. T006 beside T005.

## Implementation Strategy

**MVP is US1 and T012**: the two latent holes closed and the tests in. US2–US3 are guards that make
the seam something that is tested; US4 is what makes a hard-gated constraint mean anything, and is
the one most likely to find that a guard is weaker than it looks.
