---
description: "Tasks for REQ-WP-098 -- a second spot venue"
---

# Tasks: A second spot venue

## Phase 1: Tests (RED first)

- [X] T001 [P] `tests/unit/context/test_sources_series.py`: the series list; every perpetual a series maps to is polled; book symbols per venue; OKX spot mapped to its pair's swap
- [X] T002 [P] `tests/unit/context/test_book_stream.py`: spot vs swap sizes and market-type label; refusal of a swap without a contract value; the OKX subscription carries four instruments
- [X] T003 [P] `tests/unit/crossvenue/test_consensus_write.py`: the deployment's spot groups have two venues and aliases under both symbols
- [X] T004 [P] `tests/unit/pipeline/test_context_main.py`: settings carry book symbols apart from derivative symbols

## Phase 2: Implementation

- [X] T005 `context/sources.py`, `context/book.py`, `pipeline/context_main.py`, `crossvenue/deployment.py`
- [X] T006 `docker-compose.yml` (three ingest services), `.env.example`, `docs/deployment.md`
- [X] T007 [P] mutation specs

## Phase 3: Gate and live evidence

- [ ] T008 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit
- [ ] T009 Start the three ingests, rebuild the OKX collector, then the worker; `make panes-report`; screenshots; `implemented` after SC-001/SC-002 hold

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 ingest | T006 |
| FR-002/003 books | T002, T005 |
| FR-004 perpetuals | T001, T005 |
| FR-005 consensus | T003, T005 |
| FR-006 containers | T006, T009 |
| SC-001/002 | T009 |
| SC-003 | T002 |
