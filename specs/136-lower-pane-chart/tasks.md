---
description: "Tasks for REQ-WP-092 — the lower pane as a chart on the main chart's time axis"
---

# Tasks: The lower pane is a chart on the main chart's own time axis

**Tests** first, run RED, recorded. The existing web tests are the regression guard; edits are listed in the outcome note.

## Phase 1: Setup

- [x] T001 Record the **before**: web test count (411), bundle gzip (164,428 B), and a screenshot of the Volume and CVD panes as they are

## Phase 2: Tests first

- [x] T002 [P] [US1] `apps/web/src/__tests__/paneChartAlign.test.ts`: `alignToBars` — SC-001 (12 bars, one forming, values at 10: 12 entries at the candle times, 2 whitespace), SC-002 (a point inside a bar goes to that bar; two in one bar show the later), the boundary instant (a bar's close) goes to that bar, not the next, no bar gets no entry, no bars give none, one bar. `// @trace: REQ-WP-092`
- [x] T003 [P] [US2] `apps/web/src/__tests__/paneChartRuns.test.ts`: `runsOf` splits at `cvd_run`, never joins runs, whitespace-free; volume colours up/down by candle direction
- [x] T004 [P] [US1] `apps/web/src/__tests__/paneChartSync.test.tsx` (library mocked): a backbone series holds every bar time; series types per pane (histogram, line, one line per run); a zero price line for CVD; `minimumWidth` equal on both charts; a new pane chart takes the main chart's visible range at creation; two-way range sync with exactly one call each way and no echo; crosshair sync both ways
- [x] T005 [P] [US3] `apps/web/src/__tests__/paneChartLifecycle.test.tsx`: series replaced on a change of data, pane, scheme, palette; no throw when the main chart is removed first; the pane chart element has `role="img"` named `<feature> over N point(s)`
- [x] T006 [P] [US3] `apps/web/src/__tests__/chartHandle.test.tsx`: `Chart`'s `onReady` hands the API and `candles()` and is cleared on unmount; without `onReady` nothing changes; with the `candles` layer off the candle series holds a whitespace entry per bar time and no values
- [x] T007 [P] [US3] `apps/web/src/__tests__/flowPaneChart.test.tsx`: `FlowPane` draws the pane chart with a handle and the SVG without; roles and names of buttons and messages unchanged
- [x] T008 Run everything; confirm RED for the right reasons (missing modules and props); record the output

## Phase 3: User Stories 1 and 2 — the chart (P1) 🎯 MVP

- [x] T009 [US1] `apps/web/src/paneChart.ts`: `alignToBars`, `runsOf`, volume colours. `// @trace: REQ-WP-092`
- [x] T010 [US1] `apps/web/src/PaneChart.tsx`: the second chart, backbone, series per pane, legend, zero line, `minimumWidth`, two-way sync with a guard, crosshair sync, cleanup. `// @trace: REQ-WP-092`
- [x] T011 [US3] `apps/web/src/Chart.tsx`: optional `onReady` handle, `minimumWidth` on its right price scale, whitespace for every bar time when `candles` is off (D9); `apps/web/src/FlowPane.tsx`: `PaneChart` with a handle, the SVG without; `apps/web/src/App.tsx`: keep and pass the handle

## Phase 4: User Story 4 — looked at (P2)

- [x] T012 [US4] `specs/136-lower-pane-chart/screenshots.mjs`: live Volume and CVD, light and dark, 1280 px and 390 px, into `docs/ui/pane-{volume,cvd}-{light,dark}-{desktop,phone}.png`; rebuild and recreate `web` only; **look at every image**; measure that the plot areas' edges equal (SC-004), and note resize and a phone-width check (autoSize on both); fix and record what looking showed
- [x] T013 [P] [US4] `tests/unit/web/test_pane_chart_artifacts.py` (`@pytest.mark.trace("REQ-WP-092")`): the eight screenshots exist; the new modules and the changed ones trace

## Phase 5: Polish

- [x] T014 `make lint typecheck web-typecheck web-test web-build`; bundle gzip after; update `test_material_ui_artifacts` only if its naming-scheme check is hit
- [x] T015 Implement outcome note; set `implemented`; **one** `make graph`, then the trace `validate`; commit with explicit paths; **do not touch tracked files while the hook runs**

## Coverage

| requirement | task |
|---|---|
| FR-001 same sequence of bar times | T002, T004, T009, T010 |
| FR-002 a value at the bar that contains it | T002, T009 |
| FR-003 range and crosshair sync, no loop | T004, T010 |
| FR-004, FR-004a equal width and inset; adopt the range; the bar sequence whatever the layers | T004, T006, T010, T011, T012 |
| FR-005 title, last value, axis, zero line, per-run lines, volume colours | T003, T004, T010 |
| FR-006 roles and names; `role="img"` named | T005, T007 |
| FR-007 SVG fallback | T007, T011 |
| FR-008 replace, not accumulate; unmount order | T005, T010 |
| FR-009 live screenshots | T012, T013 |
| SC-001..SC-004 | T002, T004, T012 |
| SC-005 existing tests | T008, T014 |
| SC-006 looked at | T012 |

## Dependencies

T001 first; T002-T007 any order, then T008; T009 → T010 → T011; T012 after T011; T013 any time after T011; T014, T015 last.

## MVP

T009-T011 put Volume and CVD on the chart's own axis; the screenshots are what proves the alignment.
