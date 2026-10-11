---
description: "Tasks for REQ-WP-095 -- OFI, depth imbalance and the quotes from a top-of-book subscription"
---

# Tasks: The order-flow panes and the venue quotes are fed by a top-of-book subscription

**Input**: `spec.md`, `plan.md`. Depends on specs 145 and 146's runtime. Tests first.

## Phase 1: Evidence and fixtures

- [X] T001 Streams probed 2026-10-11; frames recorded for Binance spot depth10, Bybit orderbook.50 (snapshot + deltas), OKX books5
- [ ] T002 Copy the frames into `tests/fixtures/context/`; `tools/record/book_capture.py` reproduces them
- [ ] T003 Measure the host before any book stream runs (collector CPU baseline, MinIO health, worker cycle time) for SC-006

## Phase 2: Tests (RED first)

- [ ] T004 [P] `tests/unit/connectors/test_book_normalise.py`: each venue's frame -> `BookSnapshot`; Bybit snapshot then delta through `BookService`; OKX five levels; crossed/empty/non-positive refused with a reason
- [ ] T005 [P] `tests/unit/context/test_minute_book.py` (**the core**): a scripted sequence across a boundary -> OFI, `DI_10` (or the venue's depth), mid equal the hand calculation in `Decimal`; frames after the boundary change nothing; a silent minute is finalised on the clock with count zero; a reconnect resets the tracker and no OFI increment spans the gap
- [ ] T006 [P] `tests/unit/tables/test_book_minutes.py` and a `quotes` write test: two times apart, decimals
- [ ] T007 [P] `tests/unit/features/test_context_write_book.py`: the value at a close equals the last closed minute's; later summaries change nothing; zero-count or stale (> 2 min) writes nothing; `depth_imbalance_10` is not written for a venue whose book has fewer than ten levels
- [ ] T008 [P] `tests/mutations/context_book.toml`

## Phase 3: Implementation

- [ ] T009 normalisers; `context/minute_book.py`; `tables/book_minutes.py`
- [ ] T010 stream tasks and wiring; the 1 Hz sampling of Bybit's `BookService`
- [ ] T011 `features/context_write.py::book_rows`; registration text states the sampling and depth
- [ ] T012 compose/maintenance/docs

## Phase 4: Gate and live evidence

- [ ] T013 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit
- [ ] T014 Deploy with the collector; **measure load** (SC-006); recorded queries for SC-004/005; if the load is not acceptable, drop Bybit to `orderbook.1` and record it

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001/002 subscription, normalise, refuse | T004, T009, T010 |
| FR-003/004/006 minute finalisation, reset, zero count | T005, T009 |
| FR-005 tables, quotes | T006, T009 |
| FR-007/008 worker, no look-ahead | T007, T011 |
| FR-009 registration | T011 |
| FR-010 stalls and metrics | T010, T014 |
| FR-011 others unchanged | T014 |
| SC-001-003 | T004-T007 |
| SC-004/005 | T014 |
| SC-006 | T003, T014 |
