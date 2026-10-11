---
description: "Tasks for REQ-WP-099 -- the DEX panes get a source"
---

# Tasks: The DEX panes get a source

## Phase 1: Tests (RED first)

- [X] T001 [P] `tests/unit/connectors/hyperevm/test_rpc.py`: JSON-RPC provider -- success, error object, rate limit inside a 200, HTTP failure, timeout
- [X] T002 [P] `tests/unit/dex/test_hyperevm_collect.py`: recorded getLogs -> swaps; refusals; cursor; pieces; no double store; failure leaves cursor
- [X] T003 [P] `tests/unit/pipeline/test_dex_pass.py`: as-of rules, coverage, no-swap window, liquidity staleness, watermark
- [X] T004 [P] `tests/unit/context/test_sources_series.py`, `tests/tools/panes/test_classify.py`, `tests/unit/deploy/test_compose_logging.py`

## Phase 2: Implementation

- [X] T005 `connectors/hyperevm/rpc.py`, `dex/hyperevm_pools.py`, `dex/hyperevm_collect.py`
- [X] T006 `pipeline/dex_main.py`, `pipeline/dex_pass.py`, `pipeline/channel_main.py`, `context/sources.py`, `tools/panes`
- [X] T007 `docker-compose.yml`, `.env.example`, `docs/deployment.md`
- [X] T008 [P] mutation specs

## Phase 3: Gate and live evidence

- [ ] T009 `make lint`, `make typecheck`, `make graph`; `status: tested`; commit
- [ ] T010 Start the new services, then the worker; `make panes-report`; screenshots; `implemented` after the acceptance holds

## Coverage

| Requirement | Tasks |
|---|---|
| Collector | T001, T002, T005 |
| Features | T003, T006 |
| Deployment | T004, T007 |
