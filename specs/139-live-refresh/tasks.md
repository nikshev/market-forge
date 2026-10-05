---
description: "Tasks for REQ-WP-090 — the chart follows the market without a reload"
---

# Tasks: The chart follows the market without a reload

**Input**: Design documents from `/specs/139-live-refresh/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: The spec's acceptance scenarios are testable; tests are written first (TDD).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `apps/web/src/`, `apps/web/src/__tests__/`, `tests/unit/web/`
- Paths below follow the repository structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline metrics before changes

- [ ] T001 Record **before**: web test count (`make web-test`), bundle gzip (`cd apps/web && npm run build && gzip -c dist/assets/index-*.js | wc -c`), a screenshot of a live chart before refresh is implemented

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core timer and state infrastructure in `App.tsx` — MUST complete before any user story

- [ ] T002 Add `VITE_CHART_REFRESH_MS` to `.env.example` and `vite.config.ts` (Vite env), parsed in `App.tsx` with default 60_000; `<=0 || NaN` disables timer
- [ ] T003 Add `isLoading` ref, `timerId` ref, `lastRefreshFailed` state, `lastRefreshError` state to `App.tsx`
- [ ] T004 Add `visibilitychange` listener in `App.tsx`: clear timer on hide, one immediate refresh + restart interval on show
- [ ] T005 Add `isInitialLoad` prop to `Chart` component (from `App.tsx`): true on mount and on timeframe/mode change, false on refresh tick
- [ ] T006 Modify `Chart.tsx` range effect: only run `fitContent`/`setVisibleLogicalRange` when `isInitialLoad` is true

**Checkpoint**: Foundation ready — timer, in-flight guard, visibility, range preservation in place

---

## Phase 3: User Story 1 - A finished bar appears without a reload (Priority: P1) 🎯 MVP

**Goal**: On a live chart, a bar finalised after load appears within one configured interval (default 60 s) without a reload

**Independent Test**: With a clock and a replaced API, open a live chart, finalise a bar after load, advance the clock past the interval, and read the chart's bars

### Tests for User Story 1 (write FIRST, confirm RED)

- [ ] T007 [P] [US1] `apps/web/src/__tests__/appRefresh.test.tsx`: timer fires on interval, calls `load()`, new bars drawn; pinned chart (`at`) issues zero requests; hidden tab issues zero while hidden, one on show
- [ ] T008 [P] [US1] `apps/web/src/__tests__/chartRangePreserved.test.tsx`: `Chart` receives `isInitialLoad=false` on refresh, does not call `fitContent`/`setVisibleLogicalRange`; only `isInitialLoad=true` sets range
- [ ] T009 [P] [US1] `tests/unit/web/test_live_refresh_markers.py` (`@pytest.mark.trace("REQ-WP-090")`): modules carry `# @trace: REQ-WP-090` / `// @trace: REQ-WP-090`

### Implementation for User Story 1

- [ ] T010 [US1] `apps/web/src/App.tsx`: timer callback — check pinned (`link.atNs !== null`), hidden (`document.hidden`), disabled (`intervalMs <= 0`), `isLoading`; if any true, skip; else set `isLoading=true`, call `load()`, in `finally` set `isLoading=false`
- [ ] T011 [US1] `apps/web/src/App.tsx`: on refresh failure, `setState("failed", "Refresh failed: " + detail)`; set `lastRefreshFailed=true`, `lastRefreshError=detail`; previous `bars`, `channel`, `extrema`, `points`, `pane` state unchanged
- [ ] T012 [US1] `apps/web/src/App.tsx`: on refresh success, clear `lastRefreshFailed`, `lastRefreshError`; `load()` result updates state as normal
- [ ] T013 [US1] `apps/web/src/App.tsx`: `loadId` supersede guard already handles out-of-order answers; ensure timer tick uses same `load()` so it benefits

---

## Phase 4: User Story 2 - A refresh keeps what the reader chose (Priority: P1) 🎯 MVP

**Goal**: Timeframe, channel mode, lower pane, candidate switch, and visible range are preserved across refresh

**Independent Test**: Change each piece of state, run a refresh, read each back — all five unchanged

### Tests for User Story 2 (write FIRST, confirm RED)

- [ ] T014 [P] [US2] `apps/web/src/__tests__/appRefresh.test.tsx`: change timeframe → refresh → timeframe unchanged; change mode → refresh → mode unchanged; change pane → refresh → pane unchanged; toggle candidates → refresh → candidates unchanged; pan/zoom chart → refresh → visible range unchanged

### Implementation for User Story 2

- [ ] T015 [US2] `apps/web/src/App.tsx`: timer tick calls existing `load()` which reads current `timeframe`, `mode`, `link`, `profileWindow` from state — no reset logic added, so state is preserved automatically
- [ ] T016 [US2] `apps/web/src/Chart.tsx`: range preservation already done in T006 (`isInitialLoad` prop); confirm no other effect resets range

---

## Phase 5: User Story 3 - A pinned chart, a hidden tab and a failed refresh (Priority: P1) 🎯 MVP

**Goal**: Pinned chart never refreshes; hidden tab pauses and resumes once; failed refresh keeps picture, states failure, recovers on next success

**Independent Test**: Each with a replaced API and a clock or visibility event

### Tests for User Story 3 (write FIRST, confirm RED)

- [ ] T017 [P] [US3] `apps/web/src/__tests__/appRefresh.test.tsx`: `link.atNs !== null` → zero timer ticks over any number of intervals
- [ ] T018 [P] [US3] `apps/web/src/__tests__/appRefresh.test.tsx`: hidden tab → zero ticks; visible again → exactly one tick
- [ ] T019 [P] [US3] `apps/web/src/__tests__/loadStateRefresh.test.tsx`: refresh fails → `LoadState` shows "Refresh failed: ..." (role `alert`); chart still draws old bars; next success → notice clears, new data drawn
- [ ] T020 [P] [US3] `apps/web/src/__tests__/appRefresh.test.tsx`: overlapping ticks — second tick sees `isLoading=true` and skips; only one load in flight

### Implementation for User Story 3

- [ ] T021 [US3] `apps/web/src/App.tsx`: timer start conditional on `!pinned && !hidden && intervalMs > 0 && !isLoading` — already covered in T010
- [ ] T022 [US3] `apps/web/src/App.tsx`: `visibilitychange` listener already added in T004; verify one immediate refresh on show
- [ ] T023 [US3] `apps/web/src/LoadState.tsx`: no change needed — existing `failed` vocabulary (role `alert`) used with prefixed detail

---

## Phase 6: User Story 4 - Looked at, on the running stack (Priority: P2)

**Goal**: Live validation on running stack; interval is the configured value

### Tests for User Story 4

- [ ] T024 [US4] `specs/139-live-refresh/screenshots.mjs`: live chart on running stack, light and dark, before/after a bar finalises; into `docs/ui/refresh-{light,dark}.png`; rebuild `web` only; **look at both**
- [ ] T025 [P] [US4] `tests/unit/web/test_live_refresh_artifacts.py` (`@pytest.mark.trace("REQ-WP-090")`): the two screenshots exist; the modules trace

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T026 `make lint typecheck web-typecheck web-test web-build`; bundle gzip after
- [ ] T027 `apps/web/src/__tests__` run; all existing tests pass (regression guard)
- [ ] T028 Implement outcome note; set `implemented`; **one** `make graph`, then trace `validate`; commit with explicit paths; **do not touch tracked files while the hook runs**

---

## Coverage

| requirement | task |
|---|---|
| FR-001 refresh re-runs load | T010 |
| FR-002 interval config | T002 |
| FR-003 pinned no refresh | T010, T017 |
| FR-004 hidden tab | T004, T018 |
| FR-005 in-flight skip | T010, T020 |
| FR-006 failure keeps picture | T011, T019 |
| FR-007 reader state preserved | T015, T016 |
| FR-008 history immutable | T011 (no rewrite), T012 |
| FR-009 no push in stage 1 | N/A (spec decision) |
| SC-001 new bar in interval | T007 |
| SC-002 five states unchanged | T014 |
| SC-003 zero/one requests | T017, T018, T020 |
| SC-004 failure then recovery | T011, T012, T019 |
| SC-005 existing tests pass | T027 |

---

## Dependencies

T001 first; T002-T006 any order (foundational); T007-T013 after T006; T014-T016 after T013; T017-T023 after T016; T024-T025 after T023; T026-T028 last.

## MVP

T002-T016 deliver User Stories 1 and 2 (bar appears, state preserved); T017-T023 add User Story 3 (pinned/hidden/failure); T024-T025 is the live look.