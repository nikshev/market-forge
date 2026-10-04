---
description: "Tasks for REQ-WP-084 — candidates off by default; a pane with no data says so"
---

# Tasks: The chart hides candidate extrema until asked; a pane with no data says so

**Input**: `specs/133-chart-candidates-no-data/` (spec, plan, research, data-model, contracts, quickstart)
**Tests** first, run RED, recorded. The existing 340 web tests are the regression guard and are **not edited**
except where an edit has no accessible meaning; each one is listed in the outcome note.

## Phase 1: Setup

- [ ] T001 Record the **before**: web test count (340), bundle gzip (163,597 B), and two screenshots of the live chart (`/chart/binance/BTCUSDT?tf=15m`, light) showing the grey "?" arrows and the nine pane buttons, into the scratchpad (not committed)

## Phase 2: Tests first (all stories)

- [ ] T002 [P] [US1] Write `apps/web/src/__tests__/extremaCandidates.test.ts`: `extremumMarkers` with `includeCandidates: false` returns the three confirmed marks and with `true` seven, the same three; AS-SEEN-THEN still withholds a candidate observed after the instant with the switch on; a candidate superseded by a shown confirmation stays dropped; CURRENT REFIT adds candidates without the instant filter. `// @trace: REQ-WP-084`
- [ ] T003 [P] [US1] Write `apps/web/src/__tests__/candidateSwitch.test.tsx`: a `button` named "Candidate extrema", `aria-pressed` false then true after a press and back; calls back with the new value; present with no candidates returned
- [ ] T004 [P] [US1] Write `apps/web/src/__tests__/chartCandidates.test.tsx` (library mocked as in `chartSeriesCleanup.test.tsx`): `Chart` with confirmed + candidate extrema and no `showCandidates` is handed only the confirmed marks; with `showCandidates` it is handed both; the markers update when the prop changes without re-creating extra series
- [ ] T005 [P] [US2] Extend `apps/web/src/__tests__/panes.test.ts`: `availablePanes` (only `ofi_1m` carried → exactly that pane; empty series → none; a value of `0` is data; a feature name that is not one of the nine is ignored; gaps inside a series do not remove a pane) and `chooseSelection` (a valid choice kept; first available chosen when the choice is unavailable; none → `null`; `null` availability keeps the choice)
- [ ] T006 [P] [US2] Extend `apps/web/src/__tests__/FlowPane.test.tsx` (new cases only): with `available` a set, panes outside it are disabled buttons named "<label> no data" and a pane inside keeps its exact name and `aria-pressed`; `available` `null` and absent leave every pane pressable and none says "no data"; selection `null` shows a `status` named "Pane contents" reading "No pane has data for this view"; a failure shows its message and no "no data"
- [ ] T007 [US2] Write `apps/web/src/__tests__/chartPanesLoading.test.tsx` (fetch mocked): the page does not label any pane "no data" before the feature series has answered or when it failed; after an answer carrying only `ofi_1m` exactly one pane is a button and eight read "no data"; after an empty answer all nine do; the selection moves to the first pane with data; a valid choice survives a refetch after a timeframe round-trip; no pane has data → none selected and the "No pane has data for this view" message; the switch with a failed extrema request draws nothing extra and does not throw
- [ ] T008 Run the new tests and the whole suite: confirm they fail **for the right reason** (missing exports, absent props), the 340 existing still pass; record the RED output

## Phase 3: User Story 1 — candidates off until asked (P1) 🎯 MVP

**Goal**: the first view of a chart shows confirmed structure only; a switch shows the candidates.
**Independent test**: T002–T004 pass; the chart on the live stack has no grey arrows until the switch is pressed.

- [ ] T009 [US1] `apps/web/src/extrema.ts`: `extremumMarkers` takes `includeCandidates` (default `true`, see the analysis note in the outcome file: 13 existing call sites assert behaviour that must stay), filters candidates before the existing observed-at and superseded filters. `// @trace: REQ-WP-084`
- [ ] T010 [US1] `apps/web/src/Chart.tsx`: `showCandidates` prop (default `false`) passed to `extremumMarkers`; added to the data effect's dependency list. `// @trace: REQ-WP-084`
- [ ] T011 [P] [US1] `apps/web/src/CandidateSwitch.tsx`: a Material `ToggleButton` named "Candidate extrema" with `aria-pressed`, labelled and themed like the other controls. `// @trace: REQ-WP-084`
- [ ] T012 [US1] `apps/web/src/App.tsx`: `showCandidates` state (default `false`, not read from or written to the link), the switch placed beside the layer area above the chart, and the prop passed to `Chart`. `// @trace: REQ-WP-084`

## Phase 4: User Story 2 — a pane with no data says so (P1)

**Goal**: the pane row tells the reader what exists before a press.
**Independent test**: T005–T007 pass.

- [ ] T013 [P] [US2] `apps/web/src/panes.ts`: `availablePanes(points)` (the `PANES` features whose `paneSeries` is `ok`) and `chooseSelection(current, available)`. `// @trace: REQ-WP-084`
- [ ] T014 [US2] `apps/web/src/FlowPane.tsx`: optional `available` (set or `null`), disabled "no data" buttons, the `null` selection and its `status` message; absent `available` keeps the old behaviour exactly. `// @trace: REQ-WP-084`
- [ ] T015 [US2] `apps/web/src/App.tsx`: `pointsLoaded` (false at the start of a load, true when the feature series answers, ok or failed), `available` derived (`null` while not loaded or failed), `pane` becomes `string | null`, and the selection effect applies `chooseSelection` when availability becomes known. `// @trace: REQ-WP-084`

## Phase 5: User Story 3 — never open on an empty pane (P2)

- [ ] T016 [US3] Confirm T007 holds the three Story 3 cases (first pane with data chosen; no pane has data → none and the `status` message; a reader's valid choice survives a refetch after a timeframe round-trip) and that all three were RED in T008; add whichever is missing

## Phase 6: User Story 4 — looked at (P2)

- [ ] T017 [US4] `specs/133-chart-candidates-no-data/screenshots.mjs`: from the running build, with `/api/v1/features/timeseries` intercepted by playwright to carry `cvd` and `ofi_1m` values (the live table has none), take: candidates off, candidates on, the pane row with some panes "no data", and the live un-stubbed row (all "no data"); light and dark, into `docs/ui/`
- [ ] T018 [US4] Rebuild and recreate `web` only (`docker compose up -d --build --no-deps web`), run T017, **look at every image**; fix what the looking shows and record each thing it showed; say in the note that the populated row is a stub
- [ ] T019 [P] [US4] `tests/unit/web/test_chart_candidates_artifacts.py` (`@pytest.mark.trace("REQ-WP-084")`): the screenshots named by FR-010 exist; the new modules carry their `@trace`; every `PANES` feature still names a registered feature is already covered by `test_pane_features.py` and is not duplicated

## Phase 7: Polish

- [ ] T020 `make lint typecheck test web-typecheck web-test web-build`; record bundle gzip after and that `buildHasNoInitData` still passes
- [ ] T021 Write `vault/40-outcomes/OUT-2026-10-04-implement-chart-candidates-no-data.md` (RED output, edits to existing tests, what looking showed, the stub); set `implemented`; `make graph && make validate`; commit with explicit paths; fill the commit hash after

## Coverage

| requirement | task |
|---|---|
| FR-001 candidates off/on | T002, T004, T009, T010 |
| FR-002 off on load, not in the link | T003, T012 |
| FR-003 switch state exposed; no look-ahead | T002, T003, T009 |
| FR-004 "no data" from `paneSeries` | T005, T006, T013, T014 |
| FR-005 no new list, no new call | T013, T015 |
| FR-006 loading and failure are not "no data" | T006, T007, T015 |
| FR-007 name kept, unpressable | T006, T014 |
| FR-008 selection | T005, T007, T015 |
| FR-009 existing names unchanged | T008, T020 |
| FR-010 screenshots | T017, T018, T019 |
| SC-001 3 → 7 marks | T002 |
| SC-002 1 / 8, 9, none | T007 |
| SC-003 existing tests pass | T008, T020 |
| SC-004 looked at | T018 |

## Dependencies

T001 first; T002–T007 [P] in any order, then T008 (RED); US1 (T009 → T010 → T012, T011 parallel) and US2
(T013 → T014 → T015) are independent of each other except that T012 and T015 both edit `App.tsx` and run in
sequence; T016 after T015; T017 after both stories; T018 after T017; T019 any time after T012; T020, T021 last.

## MVP

User Story 1 alone (T009–T012) removes the noise from the first view; User Story 2 makes the row honest.
Both are P1 and ship together.
