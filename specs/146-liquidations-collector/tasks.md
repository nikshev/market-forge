---
description: "Tasks for REQ-WP-094 -- the liquidations pane is fed by each venue's liquidation stream"
---

# Tasks: The liquidations pane is fed by each venue's liquidation stream

**Input**: `spec.md`, `plan.md`. Depends on spec 145's runtime (`context/`). Tests first.

## Phase 1: Evidence and fixtures

- [X] T001 Streams probed 2026-10-11; OKX frames recorded (`posSide: long, side: sell` = a long liquidated, MAGIC-USDT)
- [ ] T002 Record frames: OKX (done), Bybit `allLiquidation` and Binance `forceOrder` -- both silent in a 4-minute probe, so `tools/record/liquidation_capture.py` waits up to a stated time; if none arrive the fixture is built from the venue's documented frame and **marked as documented, not recorded**, with that said in the test
- [ ] T003 Close the open assumption: Bybit's `S` is the liquidated position's side (documentation + any recorded frame)

## Phase 2: Tests (RED first)

- [ ] T004 [P] `tests/unit/connectors/test_liquidation_{binance,bybit,okx}.py`: the position side is the opposite of the order's; notional; OKX contracts -> base via `ctVal`; refusal of an unknown contract size, a non-positive price/qty; unmappable side -> `unknown`
- [ ] T005 [P] `tests/unit/tables/test_liquidations.py`: schema, decimals, two times, sink dedupe by identity across a simulated reconnect replay
- [ ] T006 [P] `tests/unit/context/test_streams.py`: a stream task on a fake transport/clock: silence -> reconnect, backoff capped, duplicates dropped, parse failures counted
- [ ] T007 [P] `tests/unit/features/test_context_write_liquidations.py`: window features equal `window()`; later events change nothing; no heartbeat -> no row; heartbeat + no events -> zero USD and **no** imbalance; intensity absent without volume
- [ ] T008 [P] `tests/mutations/context_liquidations.toml`

## Phase 3: Implementation

- [ ] T009 `connectors/*/liquidation.py`; `tables/liquidations.py`
- [ ] T010 `context/streams.py`; `connectors/venue.py` `CONTEXT_STREAMS`; wiring in `pipeline/context_main.py`
- [ ] T011 `features/context_write.py::liquidation_rows` and its call; heartbeat from `derivatives_state`
- [ ] T012 compose/maintenance/docs additions

## Phase 4: Gate and live evidence

- [ ] T013 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit
- [ ] T014 Deploy with the collector; a longer listen on all three venues; SC-004 recorded with the query

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001/002/003 parse, side, notional | T002-T004, T009 |
| FR-004 table, dedupe | T005, T009 |
| FR-005 silence/reconnect | T006, T010 |
| FR-006-009 worker features, heartbeat, no look-ahead | T007, T011 |
| FR-010 others unchanged | T007, T014 |
| SC-001 | T004 |
| SC-002, SC-003 | T007 |
| SC-004 | T014 |
| SC-005 | T005 |
| SC-006 | T014 |
