---
description: "Tasks for REQ-WP-088 — CVD and the trade-imbalance features, from bars"
---

# Tasks: CVD and the trade-imbalance features from the aggressor volumes the bars already carry

**Tests** first, run RED, recorded. Python tests carry `@pytest.mark.trace("REQ-WP-088")`; source carries `# @trace: REQ-WP-088`.

## Phase 1: Setup

- [ ] T001 Record the **before**: `/features/snapshot` for BTCUSDT returns `{}`; pytest and web test counts; the CVD pane reads "no data". (SC-005 was already measured: Binance qualifies for the id checks, Bybit and OKX do not.)

## Phase 2: Tests first

- [ ] T002 [P] [US1] `tests/unit/features/test_flow_bars.py`: SC-001 numbers; zero-volume bar (`delta` 0, normalised absent); first-bar `cvd_base_acceleration` absent; forming bar excluded; shuffled input gives identical rows; slope is delta over the bar's seconds
- [ ] T003 [P] [US1] `tests/unit/features/test_flow_bars_lookahead.py`: appending later bars leaves the rows at and before `t` byte-identical (SC-002)
- [ ] T004 [P] [US2] `tests/unit/features/test_flow_runs.py`: removing the middle of three bars gives two runs and no sum across the gap (SC-003); a Binance trade-id jump breaks; a bar with `last − first + 1 != trade_count` emits no row and breaks both sides; a `trade_count` of 0 is not a break; a venue without `sequential_trade_ids` breaks only on a missing bar
- [ ] T005 [P] [US3] `tests/unit/tables/test_flow_sink.py`: written once after the latest `cvd_base` row on record; a second pass over the same bars writes nothing (SC-004); a shorter series writes nothing
- [ ] T006 [P] [US3] `tests/unit/pipeline/test_channel_flow_step.py`: a fake catalog with bars: the worker pass writes flow rows for every timeframe it processes and the channel output is unchanged
- [ ] T007 [P] [US1] `tests/unit/features/test_flow_specs.py`: six `FeatureSpec`s registered, each stating its unit and the deviation from §15.4; none named `cvd` or `delta_notional`
- [ ] T008 [P] `tests/unit/connectors/test_sequential_ids.py`: the venue registry flags Binance only
- [ ] T009 [P] [US4] vitest `apps/web/src/__tests__/cvdBasePane.test.tsx`: the "CVD (base)" pane is live with rows and reads "no data" without; the line breaks where `cvd_run` changes
- [ ] T010 Run everything; confirm RED for the right reasons (missing modules, no rows); record the output; list the existing test whose expected list changes (`panes.test.ts`)

## Phase 3: User Stories 1 and 2 — the function (P1) 🎯 MVP

- [ ] T011 [US1] `src/channelflow/features/flow_bars.py`: `flow_rows(bars, *, sequential_ids)` and the run logic. `# @trace: REQ-WP-088`
- [ ] T012 [US1] `src/channelflow/features/flow.py`: six `FeatureSpec`s; `src/channelflow/connectors/venue.py`: `sequential_trade_ids` (Binance true)
- [ ] T013 [US2] Records in `vault/20-decisions/ADR-068.md` (already written at specification) are checked against what was built

## Phase 4: User Story 3 — written once, every timeframe (P1)

- [ ] T014 [US3] `src/channelflow/tables/features.py`: `flow_feature_rows` and a sink that reads the latest row on record before it writes (ADR-056)
- [ ] T015 [US3] `src/channelflow/pipeline/channel_main.py`: the flow step after the channel step in `run_series`; one failing series must not end the pass (the existing handler)

## Phase 5: User Story 4 — the pane draws it (P1)

- [ ] T016 [US4] `apps/web/src/panes.ts` (`cvd` → `cvd_base`, label "CVD (base)"), `FlowPane.tsx` (break the line where `cvd_run` changes); update the one expected line in `panes.test.ts`; `// @trace: REQ-WP-088`

## Phase 6: User Story 5 — live, and looked at (P2)

- [ ] T017 Mutation specs `tests/mutations/flow_bars.toml`; run `python -m tools.mutate`; patch what survives
- [ ] T018 Deploy: recreate `worker` and `api` **only** (check first that no time-boxed measurement is running); wait for a pass; check `/features/timeseries` returns `cvd_base` for BTCUSDT 15m
- [ ] T019 `specs/135-trade-flow-features/screenshots.mjs`: the live pane, light and dark, into `docs/ui/cvd-pane-{light,dark}.png`; **look at both**; rebuild `web`; `tests/unit/web/test_cvd_pane_artifacts.py` checks they exist and the modules trace; record what the looking showed

## Phase 7: Polish

- [ ] T020 `make lint typecheck test web-typecheck web-test web-build`; bundle gzip after
- [ ] T021 Implement outcome note; set `implemented`; **one** `make graph`, then the trace `validate`; commit with explicit paths; **do not touch tracked files while the hook runs**

## Coverage

| requirement | task |
|---|---|
| FR-001 from bars, no trade read | T002, T011 |
| FR-002 formulas; absent cases | T002, T011 |
| FR-003 no look-ahead; forming excluded | T002, T003, T011 |
| FR-004 runs and breaks | T004, T008, T011, T012 |
| FR-005 written once, every timeframe | T005, T006, T014, T015 |
| FR-006 `*_base` names with specs | T007, T012 |
| FR-007 pane draws, breaks at a run | T009, T016 |
| FR-008 live API serves `cvd_base` | T018 |
| FR-009 ADR recorded | T013 |
| FR-010 live screenshots | T019 |
| SC-001..SC-004 | T002, T003, T004, T005 |
| SC-005 measured | T001 (already measured; recorded in the spec) |
| SC-006 looked at | T019 |

## Dependencies

T001 first; T002-T009 any order, then T010; T011 → T012; T013 after T011; T014 after T011; T015 after T014; T016
any time after T009; T017 after T011-T015; T018 after T015; T019 after T018 and T016; T020, T021 last.

## MVP

T011 + T012 + T014 + T015 + T016: the function, the worker step and the pane put a CVD line on the 15m chart.
