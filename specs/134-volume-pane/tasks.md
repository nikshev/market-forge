---
description: "Tasks for REQ-WP-085 — the volume pane"
---

# Tasks: The lower panes include volume, drawn from the bars the page already loads

**Tests** first, run RED, recorded. The existing 377 web tests are the regression guard; `test_pane_features.py`
and `panes.test.ts` are **not edited**. The edits to REQ-WP-084's own new tests (they count panes) are listed in the outcome note.

## Phase 1: Setup

- [x] T001 Record the **before**: web test count (377), bundle gzip (163,887 B), the pane row as it is today

## Phase 2: Tests first

- [x] T002 [P] [US1] Write `apps/web/src/__tests__/volumePane.test.ts`: `volumeSeries` — twelve final bars and one non-final give twelve values equal to `volume_base`, at `open_time_ns`; a zero volume is a point at zero; `"12345.678901234"` survives as that number; a non-numeric `volume_base` is skipped, not zero; no final bars gives `empty`; one bar and equal volumes are valid. `// @trace: REQ-WP-085`
- [x] T003 [P] [US2] Write `apps/web/src/__tests__/volumeAvailability.test.ts`: `availablePanes(points, bars)` has `volume` iff a final bar exists, and the feature panes are as before; `chooseSelection` picks Volume first when it has data; `ROW` is `BAR_PANES` then `PANES` and `PANES` is unchanged
- [x] T004 [P] [US1] Write `apps/web/src/__tests__/flowPaneVolume.test.tsx`: Volume is the first button; selected, an `img` named `volume over N point(s)` holds one rect per final bar; with bars and a feature `failure` the failure message is absent and Volume still draws, while a selected feature pane still shows it; no bars gives a disabled "Volume no data"
- [x] T005 [US2] Write `apps/web/src/__tests__/chartVolumeOpens.test.tsx` (API mocked as in `chartPanesLoading.test.tsx`): with bars and an empty feature series the page opens on Volume and shows no "No pane has data" message; with a failed feature load Volume is live and no pane says "no data"; the bar load answering with no bars at all makes Volume "no data" at once (the feature series is never requested); before the bars have answered Volume says nothing; with bars and OFI data a reader's choice of OFI survives a refetch
- [x] T006 Run the new tests and the whole suite: confirm they fail for the right reason (missing exports, no Volume button), record the RED output, and list which of REQ-WP-084's own tests now fail because they count panes

## Phase 3: User Story 1 and 2 — Volume, live and independent (P1) 🎯 MVP

- [x] T007 [US1] `apps/web/src/panes.ts`: `BAR_PANES`, `ROW`, `volumeSeries(bars)`, `availablePanes(points, bars = [])`, `chooseSelection` over `ROW`; rewrite the comment above the lists (FR-007). `// @trace: REQ-WP-085`
- [x] T008 [US1] `apps/web/src/FlowPane.tsx`: `bars` prop (default `[]`) and `barsLoaded` (default `false`; Volume is "no data" iff it is true and the series is not `ok`), render `ROW`, draw a bar-sourced pane as vertical bars, show the feature failure only when a feature pane is selected. `// @trace: REQ-WP-085`
- [x] T009 [US2] `apps/web/src/App.tsx`: `barsLoaded` state (true when `fetchBars` answers ok), passed with `bars` to `FlowPane` and `bars` to `availablePanes`; the initial pane is the first of `ROW`. `// @trace: REQ-WP-085`
- [x] T010 Update REQ-WP-084's own pane-counting tests (`flowPaneAvailability`, `chartPanesLoading`) for the tenth pane and for Volume being the first with data; list each edit and why

## Phase 4: User Story 3 — the claim is true (P2)

- [x] T011 [US3] Covered by T007; read the new comment against `PANES` and PRD §27.3 line by line, and record the check in the outcome note (a comment cannot be asserted by a test without asserting its words)

## Phase 5: User Story 4 — looked at (P2)

- [x] T012 [US4] `specs/134-volume-pane/screenshots.mjs`: from the running build, **live, no stub**, the chart with Volume selected, light and dark, into `docs/ui/volume-pane-{light,dark}.png`
- [x] T013 [US4] Rebuild and recreate `web` only; run it; **look at both**; fix what the looking shows and record each thing
- [x] T014 [P] [US4] `tests/unit/web/test_volume_pane_artifacts.py` (`@pytest.mark.trace("REQ-WP-085")`): the two screenshots exist; `panes.ts`, `FlowPane.tsx`, `App.tsx` carry `// @trace: REQ-WP-085`

## Phase 6: Polish

- [x] T015 `make lint typecheck web-typecheck web-test web-build`; bundle gzip after; `buildHasNoInitData` still passes
- [x] T016 Implement outcome note; set `implemented`; **one** `make graph` (it runs the whole suite) then the trace `validate`; commit with explicit paths

## Coverage

| requirement | task |
|---|---|
| FR-001 Volume first | T003, T004, T007, T008 |
| FR-002 `PANES` stays features | T003, T007 |
| FR-003 one value per final bar; zero; non-final | T002, T004 |
| FR-004 precise parse; non-numeric skipped | T002 |
| FR-005 no data; independent of features | T004, T005, T008 |
| FR-006 opens on first with data; no override | T003, T005, T009 |
| FR-007 comment true | T007, T011 |
| FR-008 live screenshots | T012, T013, T014 |
| SC-001 twelve values | T002 |
| SC-002 one live pane, three states | T005 |
| SC-003 existing tests pass | T006, T015 |
| SC-004 looked at | T013 |

## Dependencies

T001 first; T002-T005 in any order, then T006; T007 → T008 → T009 → T010; T011 after T007; T012 → T013;
T014 any time after T009; T015 and T016 last. T008 and T009 edit different files, T007 first.
