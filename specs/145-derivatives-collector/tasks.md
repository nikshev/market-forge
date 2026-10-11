---
description: "Tasks for REQ-WP-093 -- the derivatives panes are fed by a collector"
---

# Tasks: The derivatives panes are fed by a collector

**Input**: `spec.md`, `plan.md`. Tests first; the RED output goes into the implementation outcome note.

## Phase 1: Evidence and fixtures

- [X] T001 Probe every REST endpoint and stream from this host (done 2026-10-11, recorded in the spec's Context)
- [ ] T002 [P] Record fixtures under `tests/fixtures/context/` for Binance (`premiumIndex`, `openInterestHist`, `fundingRate`, `fundingInfo` excerpt), Bybit (`tickers`, `funding/history`, `instruments-info`) and OKX (`open-interest`, `funding-rate`, `mark-price`, `index-tickers`, `funding-rate-history`, `instruments`); `tools/record/derivatives_capture.py` reproduces them

## Phase 2: Tests (RED first)

- [ ] T003 [P] `tests/unit/connectors/test_derivatives_state_usd.py`: Binance state from `premiumIndex` + `openInterestHist` carries USD OI with event time = the bucket's; Bybit's event time is the response's `time`, not receipt; missing fields are absent, never defaults
- [ ] T004 [P] `tests/unit/connectors/test_funding_history.py`: each venue's history rows -> `DerivativesState` with `event_time == next_funding_time == settlement`, rate exact, source tag `history`; the interval per venue is read from the venue's own fields
- [ ] T005 [P] `tests/unit/tables/test_derivatives_state.py`: schema (§10.4 + source tag + ingest time), decimals not floats, round trip, sink dedupe by identity, idempotent flush
- [ ] T006 [P] `tests/unit/context/test_rest.py`: a failed, non-200, rate-limited (429, 418 with `Retry-After`) or unparseable response stores nothing, counts, and backs off; a timeout never hangs the loop
- [ ] T007 [P] `tests/unit/context/test_pollers.py`: a poll returns a state per venue from the fixtures; a failing sub-request makes the whole poll store nothing; the previous state is never re-emitted; the history load is idempotent and refreshed hourly on a fake clock
- [ ] T008 [P] `tests/unit/features/test_context_write.py` (**the core**): as-of evaluation at a bar's close equals the library at that instant; appending later states changes nothing (SC-002); funding uses only `history` rows and only settled ones; staleness per feature (a gap writes nothing); too-few settlements and a constant series write nothing; per-feature watermark makes a second pass write nothing; the six trade features are untouched; a spot series is given its venue's perpetual (FR-012)
- [ ] T009 [P] `tests/unit/context/test_status.py`: `/healthz` false when the newest poll is older than 3 intervals or failures are consecutive; `/metrics` names
- [ ] T010 [P] `tests/unit/features/test_context_registrations.py`: the three features' registrations state their source and staleness

## Phase 3: Implementation

- [ ] T011 `connectors/{binance,bybit,okx}/normalize.py`: USD OI (Binance from hist), Bybit venue time, funding-history normalisers
- [ ] T012 `tables/derivatives_state.py`
- [ ] T013 `context/{sources,rest,pollers,runtime,status}.py`, `pipeline/context_main.py`
- [ ] T014 `features/context_write.py` (`write_context_features`, bisect-based), one call in `pipeline/channel_main.py`
- [ ] T015 [P] `tests/mutations/context_{normalize,pollers,write,tables}.toml` with every survivor reasoned

## Phase 4: Deployment artefacts

- [ ] T016 `docker-compose.yml` (three `context-*` services, healthcheck on `/healthz`), `deploy/prometheus/prometheus.yml` (targets), `.env.example`, `docs/deployment.md`, `pipeline/maintenance_main.py` TABLES
- [ ] T017 No-write replay of `write_context_features` on a copy of the real lakehouse with the live states (after the collectors have run a while): counts, a sample against hand evaluation, time taken

## Phase 5: Gate and live evidence

- [ ] T018 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit with explicit paths
- [ ] T019 Start the collectors (`docker compose up -d --no-deps context-binance context-bybit context-okx`); read each log first; confirm no existing container was recreated (start times)
- [ ] T020 After the worker rebuild (held until T017): SC-001, SC-005, SC-006 recorded; `status: implemented`

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001/002/003 poll, USD OI, two times | T003, T011, T012, T013 |
| FR-004 failures store nothing | T006, T007 |
| FR-005 history, hourly refresh, history-only funding | T004, T007, T008 |
| FR-006 table, maintenance | T005, T012, T016 |
| FR-007-011 worker pass, as-of, staleness, watermark | T008, T014 |
| FR-012 spot series -> perpetual | T008, T013 |
| FR-013 health/metrics | T009, T013, T016 |
| FR-014 compose, no recreation | T016, T019 |
| FR-015 six features unchanged | T008, T017 |
| SC-001 | T020 |
| SC-002 | T008 |
| SC-003 | T008 |
| SC-004 | T007 |
| SC-005 | T017, T020 |
| SC-006 | T019, T020 |
