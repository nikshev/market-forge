---
description: "Tasks for REQ-WP-091 — cross-venue consensus mid and venue basis"
---

# Tasks: Cross-venue consensus mid and venue basis

**Input**: Design documents from `/specs/140-cross-venue-consensus/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Written first (TDD) per spec acceptance scenarios.

**Organization**: Tasks grouped by user story for independent implementation/testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story (US1-US5)
- Exact file paths in descriptions

## Path Conventions

- **Python**: `src/channelflow/`, `tests/unit/`, `tests/integration/`
- **Web**: `apps/web/src/`, `apps/web/src/__tests__/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record baseline metrics

- [ ] T001 Record **before**: Python test count, web test count, bundle gzip, screenshot of chart without consensus

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure — MUST complete before any user story

- [ ] T002 Add `CHANNELFLOW_CONSENSUS_INTERVAL` and `CHANNELFLOW_CONSENSUS_STALENESS_NS` to `.env.example` (defaults 5m, 60s)
- [ ] T003 Create `quotes` table schema in `src/channelflow/tables/quotes.py` (venue, symbol, bid, ask, mid, ts_ns, ingest_ns)
- [ ] T004 Create `consensus` table schema in `src/channelflow/tables/consensus.py` (asset, market_type, bar_close_ns, consensus_mid, venue_count, refusal_reason)
- [ ] T005 Add `venue_basis_bps` to `FeatureSpec` registry in `src/channelflow/features/__init__.py` (unit=bps, cadence=bar_close, source=cross-venue)
- [ ] T006 Add `venue_basis_bps` to pane list in `apps/web/src/panes.ts` (ROW entry, line series)

**Checkpoint**: Tables, config, feature registry, pane list ready

---

## Phase 3: User Story 1 - Consensus mid library correctness (Priority: P1) 🎯 MVP

**Goal**: `consensus_mid` returns median of fresh mids from ≥2 venues; excludes stale/future; refuses one venue

**Independent Test**: Call `consensus_mid` with fixture quotes; verify median, exclusions, refusals

### Tests for US1 (write FIRST, confirm RED)

- [ ] T007 [P] [US1] `tests/unit/crossvenue/test_consensus.py`: median of 2/3 fresh mids; stale excluded with reason; future excluded with reason; one venue refuses; consensus at `t` unchanged when later quotes appended (no look-ahead)

### Implementation for US1

- [ ] T008 [US1] `src/channelflow/crossvenue/consensus.py`: verify `consensus_mid` already enforces all rules (it does per REQ-WP-016); add docstring with acceptance scenarios
- [ ] T009 [US1] `tests/unit/crossvenue/test_consensus.py`: ensure all acceptance scenarios covered (already in T007)

---

## Phase 4: User Story 2 - API serves consensus and venue basis (Priority: P1)

**Goal**: `GET /api/v1/consensus` returns per-bar consensus for windows; `GET /api/v1/features/timeseries?feature=venue_basis_bps` returns basis

**Independent Test**: Call endpoints with fixture data; verify responses

### Tests for US2 (write FIRST, confirm RED)

- [ ] T010 [P] [US2] `tests/unit/api/test_consensus_endpoint.py`: consensus endpoint returns per-bar mids with venue_count/refusal_reason; window validation (4h/24h/7d); `at_ns` point-in-time
- [ ] T011 [P] [US2] `tests/unit/api/test_venue_basis_endpoint.py`: basis endpoint returns `venue_basis_bps` points; `feature=venue_basis_bps` required; `start_ns`/`end_ns` window

### Implementation for US2

- [ ] T012 [US2] `src/channelflow/api/repositories.py`: add `get_consensus`, `get_venue_basis` queries (read consensus table + viewed venue's quote at bar_close_ns)
- [ ] T013 [US2] `src/channelflow/api/routes.py`: add `/consensus` and extend `/features/timeseries` for `venue_basis_bps`
- [ ] T014 [US2] `src/channelflow/api/schemas.py`: add `ConsensusOut`, `VenueBasisOut` response models

---

## Phase 5: User Story 3 - Chart draws consensus line (Priority: P1)

**Goal**: Optional chart layer draws consensus line at bar mids; gaps where <2 venues; notice at gaps

**Independent Test**: Render chart with consensus data; verify line and gaps

### Tests for US3 (write FIRST, confirm RED)

- [ ] T015 [P] [US3] `apps/web/src/__tests__/consensus.test.tsx`: layer on → line at consensus mids; layer off → nothing; gaps where <2 venues → no line segment, notice at gap; distinct style from channel

### Implementation for US3

- [ ] T016 [US3] `apps/web/src/api.ts`: add `fetchConsensus` (calls `/api/v1/consensus`)
- [ ] T017 [US3] `apps/web/src/Chart.tsx`: add consensus line layer (line series at bar close times with consensus mid price); respect `overlays.consensus` flag
- [ ] T018 [US3] `apps/web/src/types.ts`: add `ConsensusOut` type
- [ ] T019 [US3] `apps/web/src/App.tsx`: fetch consensus when `overlays.consensus` is on; pass to `Chart`

---

## Phase 6: User Story 4 - Lower pane draws venue basis (Priority: P1)

**Goal**: Pane selector includes `venue_basis_bps`; draws line series aligned to bars

**Independent Test**: Select pane → line series at bar basis points

### Tests for US4 (write FIRST, confirm RED)

- [ ] T020 [P] [US4] `apps/web/src/__tests__/venueBasis.test.tsx`: pane selector shows `venue_basis_bps`; selecting it draws line series; feature registered with correct FeatureSpec

### Implementation for US4

- [ ] T021 [US4] `apps/web/src/api.ts`: `fetchVenueBasis` calls `/features/timeseries?feature=venue_basis_bps`
- [ ] T022 [US4] `apps/web/src/types.ts`: add `VenueBasisOut` type
- [ ] T023 [US4] `apps/web/src/panes.ts`: ensure `venue_basis_bps` in ROW with correct line series rendering
- [ ] T024 [US4] `apps/web/src/App.tsx`: fetch basis when pane selected; pass to `FlowPane`

---

## Phase 7: User Story 5 - Mixed instrument types rule (Priority: P2)

**Goal**: Consensus per market type (spot/perp); viewed venue uses its type's consensus; test pins rule

**Independent Test**: Fixture with Binance spot + Bybit/OKX perps → spot consensus refused (<2), perp consensus from Bybit+OKX, Bybit basis uses perp consensus

### Tests for US5 (write FIRST, confirm RED)

- [ ] T025 [P] [US5] `tests/unit/crossvenue/test_mixed_types.py`: registry provides market_type; consensus grouped by type; viewed venue uses its type's consensus; test pins rule

### Implementation for US5

- [ ] T026 [US5] `src/channelflow/api/repositories.py`: `get_consensus` filters by `market_type` from registry
- [ ] T027 [US5] `src/channelflow/instrument_metadata.py`: ensure market_type available per venue
- [ ] T028 [US5] `tests/unit/crossvenue/test_mixed_types.py`: fixture test (already in T025)

---

## Phase 8: Polish & Cross-Cutting

- [ ] T029 `make lint typecheck web-typecheck web-test web-build`; bundle gzip after
- [ ] T030 `tests/unit/crossvenue/`, `tests/unit/api/`, `apps/web/src/__tests__/` run; all existing tests pass
- [ ] T031 Screenshots: chart with consensus line (light/dark), basis pane (light/dark) → `docs/ui/consensus-{light,dark}.png`, `docs/ui/basis-{light,dark}.png`; **look at all four**
- [ ] T032 `tests/unit/web/test_cross_venue_artifacts.py` (`@pytest.mark.trace("REQ-WP-091")`): screenshots exist; modules trace
- [ ] T033 Outcome note; set `implemented`; `make graph && make validate`; commit with explicit paths

---

## Coverage

| requirement | task |
|---|---|
| FR-001 consensus_mid | T007, T008 |
| FR-002 API consensus | T010, T012, T013, T014 |
| FR-003 API venue_basis_bps | T011, T012, T013, T014 |
| FR-004 chart consensus line | T015, T016, T017, T018, T019 |
| FR-005 basis pane | T020, T021, T022, T023, T024 |
| FR-006 mixed types | T025, T026, T027, T028 |
| FR-007 screenshots | T031, T032 |
| SC-001 median/exclusions | T007 |
| SC-002 no look-ahead | T007 |
| SC-003 API responses | T010, T011 |
| SC-004 chart line/gaps | T015 |
| SC-005 pane/feature | T020 |
| SC-006 existing tests | T030 |

---

## Dependencies

T001 first; T002-T006 any order (foundational); T007-T009 after T006; T010-T014 after T009; T015-T019 after T014; T020-T024 after T014; T025-T028 after T024; T029-T033 last.

## MVP

US1 + US2 + US3 + US4 deliver consensus line and basis pane; US5 adds mixed-type rule; T031 is live look.