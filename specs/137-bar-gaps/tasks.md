---
description: "Tasks for REQ-WP-086 — a missing bar is visibly missing"
---

# Tasks: A missing bar is visibly missing

**Tests** first, run RED, recorded. The existing web tests are the regression guard; edits are listed in the outcome note.

## Phase 1: Setup

- [x] T001 Record the **before**: web test count (446), bundle gzip (166,199 B), a screenshot of ETHUSDT 1h with its hole unmarked

## Phase 2: Tests first

- [x] T002 [P] [US1] `apps/web/src/__tests__/gaps.test.ts`: `findGaps` — SC-001 (bars 0,1,2,6,7 give one gap of 3; 0,1,3 one of 1; two holes two gaps), no gap for contiguous bars, none at the ends, unsorted input, a corrected bar with the same open is not a gap, a misaligned series rounds the count and keeps the span, volume zero is not a gap; `describeGap` and `noticeLines` (UTC span, most recent first, cap of five with the rest counted). `// @trace: REQ-WP-086`
- [x] T003 [P] [US1] `apps/web/src/__tests__/chartGapMarkers.test.tsx` (library mocked): one amber marker at the first bar after a hole with text `N missing`, none for contiguous bars, all marks in one call ordered by time, a signal marker at the same bar still reaches the library
- [x] T004 [P] [US2] `apps/web/src/__tests__/gapNotice.test.tsx`: `GapNotice` role `status` named "Gaps in the bars", lists N and span, capped at five with a count, absent without gaps
- [x] T005 [P] [US3] `apps/web/src/__tests__/paneChartGaps.test.tsx` (library mocked): the histogram carries the markers at bars with a value; a CVD run whose first point is at a gap marker's time carries one, and a run that starts after a trade-id break (its first point at no gap marker's time) does not
- [x] T006 Run everything; confirm RED for the right reasons; record the output

## Phase 3: User Stories 1 and 2 — marked and said (P1) 🎯 MVP

- [x] T007 [US1] `apps/web/src/gaps.ts`: `findGaps`, `gapMarkers`, `describeGap`, `noticeLines`. `// @trace: REQ-WP-086`
- [x] T008 [US1] `apps/web/src/Chart.tsx`: merge the gap markers into the single marker list, sorted by time. `// @trace: REQ-WP-086`
- [x] T009 [US2] `apps/web/src/GapNotice.tsx` and `apps/web/src/App.tsx`: the notice under the chart. `// @trace: REQ-WP-086`

## Phase 4: User Story 3 — the pane agrees (P2)

- [x] T010 [US3] `apps/web/src/PaneChart.tsx`: the markers on the histogram and on the first point of a CVD run that starts at a gap. `// @trace: REQ-WP-086`

## Phase 5: User Story 4 — looked at (P2)

- [x] T011 [US4] `specs/137-bar-gaps/screenshots.mjs`: ETHUSDT 1h and BTCUSDT 15m, live, light and dark, into `docs/ui/gaps-{eth1h,btc15m}-{light,dark}.png`; rebuild `web` only; **look at all four**; fix and record what looking showed
- [x] T012 [P] [US4] `tests/unit/web/test_bar_gaps_artifacts.py` (`@pytest.mark.trace("REQ-WP-086")`): the four screenshots exist; the modules trace

## Phase 6: Polish

- [x] T013 `make lint typecheck web-typecheck web-test web-build`; bundle gzip after
- [x] T014 Implement outcome note; set `implemented`; **one** `make graph`, then the trace `validate`; commit with explicit paths; **do not touch tracked files while the hook runs**

## Coverage

| requirement | task |
|---|---|
| FR-001 gap from the bars' windows | T002, T007 |
| FR-002 one marker per gap, one ordered call | T003, T008 |
| FR-003 a bar that exists is no gap | T002 |
| FR-004 the notice | T002, T004, T009 |
| FR-005 pane markers | T005, T010 |
| FR-006 axis unchanged | T006, T013 |
| FR-007 live screenshots | T011, T012 |
| SC-001..SC-003 | T002, T003, T004, T011 |
| SC-004 existing tests | T006, T013 |
| SC-005 looked at | T011 |

## Dependencies

T001 first; T002-T005 any order, then T006; T007 → T008 → T009; T010 after T007; T011 after T009 and T010; T012 any time after T010; T013, T014 last.

## MVP

T007-T009 mark the gap on the chart and say it in words; T010 makes the pane agree.
