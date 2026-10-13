---
description: "Tasks for REQ-WP-102 -- a live chart"
---

# Tasks: A live chart

## Phase 1: Tests (RED first)

- [X] T001 [P] `tests/unit/bars/test_forming.py`: the builder's forming bars
- [X] T002 [P] `tests/unit/live/test_messages.py`, `test_publisher.py`: wire form, throttle, best effort
- [X] T003 [P] `tests/unit/live/test_relay.py`, `tests/unit/api/test_ws_live.py`: cache, precedence, snapshot, filtering
- [X] T004 [P] `apps/web/src/__tests__/live*.test.ts(x)`: merge, state, in-place update, panes, reconnect

## Phase 2: Implementation

- [X] T005 `bars/builder.py`, `live/*`, `pipeline/ingest*.py`
- [X] T006 `api/ws.py`, `api/main.py`, compose, nginx, `.env.example`, docs
- [X] T007 web: `live.ts`, `useLiveBars.ts`, `Chart.tsx`, `PaneChart.tsx`, `App.tsx`
- [X] T008 [P] mutation specs

## Phase 3: Gate and live evidence

- [ ] T009 lint, typecheck, `make graph`, `status: tested`, commit
- [ ] T010 deploy; measure the last bar's age in a browser; `implemented`
