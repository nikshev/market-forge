---
description: "Task list for REQ-WP-073 — bars at every configured timeframe"
---

# Tasks: Bars at every configured timeframe

**Input**: Design documents from `/specs/117-timeframe-resampling/`

**Tests**: REQUIRED. Every test carries `@pytest.mark.trace("REQ-WP-073")`.
Write each test first and watch it fail for the stated reason — a test that
passes on first run has not shown you what it guards.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project: `src/channelflow/`, `tests/` at repository root.

---

## Phase 1: Setup

- [x] T001 Record the baseline in the implement outcome note, read from the running stack: `rows=89`, `full_read=132ms`, `timeframes present: [60000000000]`. This is the "before" the feature is measured against, and it is gone once the first pass runs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the timeframe vocabulary every story reads. Nothing here touches a
table.

- [x] T002 Create `src/channelflow/timeframes.py` with `# @trace: REQ-WP-073`: frozen `Timeframe(token, ns, origin_ns)`, refusing `ns <= 0` and `origin_ns` outside `[0, ns)`, plus `CalendarPeriod` and `UnknownTimeframe`
- [x] T003 [P] Write the failing test in `tests/unit/test_timeframes.py` that `Timeframe("1w", 604800 * 10**9, 604800 * 10**9)` is refused — an origin of a whole duration is the same alignment spelled confusingly, and permitting it lets two equivalent values compare unequal
- [x] T004 Add `TIMEFRAMES`: the eight known tokens of `data-model.md`, with `1w` carrying `origin_ns = 345_600_000_000_000` and every other carrying `0`; and `SOURCE_TOKEN = "1m"`, the one timeframe nothing resamples because the ingest daemon produces it
- [x] T005 [P] Write the failing test that every entry's `token` matches its key and that every `ns` is a whole multiple of `TIMEFRAMES["1m"].ns` — a table written by hand needs a check that reads it back
- [x] T006 Add `window_start(t_ns, timeframe)` as `((t - origin) // ns) * ns + origin`
- [x] T007 [P] Write the failing test that a weekly window containing a **Thursday** opens on the preceding Monday: `2026-09-17T09:15:00Z` → `2026-09-14T00:00:00Z`, and `2026-09-13T23:59:59Z` → `2026-09-07T00:00:00Z`. Naive floor division gives 2026-09-17 and 2026-09-10 — this is the test the whole origin mechanism exists for
- [x] T008 [P] Write the failing test that `window_start` is idempotent for every known timeframe: `window_start(window_start(t)) == window_start(t)`
- [x] T009 [P] Write the failing test that pins **floor division**, not truncation: `window_start(0, TIMEFRAMES["1w"])` is `-259_200_000_000_000` (1969-12-29, a Monday). No stored bar can reach this — `Bar.open_time_ns` is `Field(ge=0)` — but the same arithmetic is destined for TypeScript, where `Math.trunc` gives a Thursday again
- [x] T010 Add `parse(token)` and `parse_list(text)`: unknown token raises `UnknownTimeframe` naming the token and listing the known ones; `1M` and any calendar period raise `CalendarPeriod` naming the calendar-month problem; `parse_list` returns sorted, de-duplicated, and raises on an empty result
- [x] T011 [P] Write the failing test that `parse("1M")` raises `CalendarPeriod` and that its message mentions the varying length of a month — the refusal has to teach, or the next person adds `2592000000000000`
- [x] T012 [P] Write the failing test that `parse_list("")` and `parse_list(" , ")` raise rather than returning an empty tuple — a deployment producing no timeframes is a mistake that looks like a quiet market
- [x] T013 [P] Write the failing test that `parse_list("1h,5m,1h")` equals `parse_list("5m,1h")` — two spellings of one configuration must behave identically

**Checkpoint**: the vocabulary exists and is proven. No bar has moved.

---

## Phase 3: User Story 2 — The values are the aggregation, exactly (Priority: P1) 🎯 MVP

**Goal**: the fold, as a pure function. This goes before User Story 1 because
US1 is this function plus plumbing, and a wrong fold plumbed correctly is worse
than no fold at all.

**Independent Test**: five `Bar` values in, one `Bar` out, compared field by
field against an aggregation computed by hand in the test.

- [x] T014 Create `src/channelflow/pipeline/resample.py` with `# @trace: REQ-WP-073` and `fold(window_bars, *, venue, symbol, target) -> Bar`
- [x] T015 [P] Write the failing test over five minutes that **differ in every field**, with the high in the third minute and the low in the fourth: `open` from the first, `close` from the last, `high`/`low` from the minutes holding them, and `volume_base`, `volume_quote`, `trade_count`, `aggressive_buy_base`, `aggressive_sell_base` summed. An implementation reading only the ends passes a lazier fixture and fails this one
- [x] T016 [P] Write the failing test that `vwap` over minutes of **unequal volume** equals `volume_quote / volume_base` of the sums, and is *not* the mean of the five minute vwaps. Assert the two differ in the fixture, so the test cannot pass by coincidence
- [x] T017 [P] Write the failing test that `vwap` falls back to `close` when `volume_base` is zero, matching `builder.py:176` — a resampled bar and a builder-produced bar of the same window must agree
- [x] T018 [P] Write the failing test that `delta_base` equals `aggressive_buy_base - aggressive_sell_base` of the summed sides
- [x] T019 [P] Write the failing test that `high_time_ns` and `low_time_ns` come from the minutes holding the extremes, not from the window's own bounds
- [x] T020 [P] Write the failing test that the folded bar carries `open_time_ns` equal to the window start, `close_time_ns` equal to `open + target.ns`, `timeframe_ns` equal to `target.ns`, and `is_final` true

**Checkpoint**: the arithmetic is right in isolation.

---

## Phase 4: User Story 1 — A higher timeframe has a series (Priority: P1)

**Goal**: windows, completeness, and the refusal — still with no table.

**Independent Test**: a list of one-minute bars and a `now_ns` in, bars and
refusals out.

- [x] T021 Add `Refusal` and `ResampleResult` to `resample.py` per `data-model.md`
- [x] T022 Add `resample(source, *, target, source_timeframe, already_present, now_ns) -> ResampleResult`, grouping by `window_start`, emitting only windows that are closed (`close_time_ns <= now_ns`) and complete (`len(window) == target.ns // source_timeframe.ns`)
- [x] T023 [P] Write the failing test that a window **missing one minute of five** produces no bar and one `Refusal` naming `expected=5`, `present=4` and the window's open time. This is the condition [[REQ-NRT-UPSAMPLE]] owns; here it is checked as this feature's own behaviour
- [x] T024 [P] Write the failing test that a window still in progress (`close_time_ns > now_ns`) produces **neither a bar nor a refusal** — nothing about it is wrong yet, and refusing it would report a problem every pass
- [x] T025 [P] Write the failing test that shuffling `source` changes nothing in the result — grouping must not depend on arrival order
- [x] T026 [P] Write the failing test that an empty `source` gives an empty result and raises nothing
- [x] T027 [P] Write the failing test that `target.ns % source_timeframe.ns != 0` raises before any window is considered — such windows cannot tile the source
- [x] T028 [P] Write the failing test that a `1d` target over 1440 complete minutes produces exactly one bar whose open time is UTC midnight

**Checkpoint**: the producer is correct and has never seen a catalog.

---

## Phase 5: User Story 4 — Running it again changes nothing (Priority: P2)

**Goal**: idempotence, which the storage layer does not provide.

**Independent Test**: feed the first result's open times back as
`already_present` and get an empty `bars` with a matching `skipped`.

- [x] T029 [P] Write the failing test that with `already_present` holding every open time from a previous result, `bars` is empty and `skipped` equals that count — **not** `written=0, skipped=0`, which is what a pass that read nothing also reports
- [x] T030 [P] Write the failing test that a window in `already_present` but *incomplete* in the source produces neither a bar nor a refusal — it is already written and is not this pass's business

**Checkpoint**: a second pass is provably a no-op.

---

## Phase 6: User Story 3 — A timeframe is added by configuration (Priority: P2)

**Goal**: the wiring, and the proof that nothing holds the set as a constant.

- [x] T031 Create `src/channelflow/pipeline/resample_main.py` with `# @trace: REQ-WP-073`: reads `CHANNELFLOW_TIMEFRAMES` through `parse_list`, opens the catalog through `settings_from_env`, and for each `(venue, symbol, target)` reads the source series and the target's existing open times, calls `resample`, appends through `BarSink`
- [x] T031a Add `ResampleReport` per `data-model.md` — what the pass **committed**, not what `resample` computed. The two are separate types for the reason the data model gives: a pass can compute ten bars and fail to append them, and one type cannot honestly carry both
- [x] T031b [P] Write the failing test that a `ResampleReport` built from a result whose append failed reports `written=0` while the result held bars — the case that justifies the second type
- [x] T032 Print one report line per series and **every refusal** to stdout, and keep going when one series fails, naming it — the rule `maintenance_main` already follows
- [x] T033 [P] Write the failing test that `--once` exits zero when nothing was written because everything already existed — a pass with nothing to do is success, not silence to be confused with failure
- [x] T034 [P] Write the failing test that configuring `4h` — a timeframe outside §5.1's four, which no existing fixture uses — produces its series, with **no source file naming `4h`**. Assert by grepping the source tree in the test, so a hard-coded set fails here rather than in review
- [x] T035 Add `CHANNELFLOW_TIMEFRAMES=5m,15m,30m,1h,4h,1d,1w` to `.env.example`, with a comment stating that `1m` is the source and is produced by the ingest daemon, not by resampling
- [x] T036 Add the `resample` service to `docker-compose.yml`, built from this repository like the other four, on a loop, depending on `postgres` and `minio` being healthy

**Checkpoint**: seven series exist on the running stack.

---

## Phase 7: Polish & Cross-Cutting

- [x] T037 Run `quickstart.md` section 2 against the running stack and record the measured before/after in the implement outcome note, including `duplicate keys: 0` after a second pass
- [x] T038 Update `docs/deployment.md`: the tenth service, what `CHANNELFLOW_TIMEFRAMES` means, and that `1M` is refused. `tests/unit/docs/test_deployment_doc.py` checks every name in that file is real, so this is not optional
- [x] T039 `make lint`, `make typecheck`, then `make graph && make validate`

---

## Dependencies & Execution Order

- **Phase 2** blocks everything: no story can group a window without `Timeframe`.
- **Phase 3 (US2)** before **Phase 4 (US1)**: the fold is the thing US1 plumbs.
- **Phase 5 (US4)** depends on Phase 4's `ResampleResult`.
- **Phase 6 (US3)** depends on Phases 3–5 and is the only phase that touches a
  catalog, compose file or environment.
- **Phase 7** last.

### Parallel Opportunities

Every `[P]` task is a test in its own file or an independent assertion in a new
file; they can be written together. The non-`[P]` tasks each create or extend
one module and must be sequential within their phase.

---

## Notes

- **Write the test first and watch it fail.** T007 in particular: if it passes
  before `origin_ns` is wired in, the fixture is wrong, not the code.
- The whole suite is unit-level and needs no live service, so all of it runs in
  the fast gate.
- T034 asserts a property of the source tree rather than of a value. That is
  deliberate: FR-002 is about where a set is *not*, and no runtime assertion can
  see an absence.
