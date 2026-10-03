---
description: "Tasks for REQ-WP-081 — the markets the stack ingests are listed, with the market type the venue's stream really is"
---

# Tasks: The markets the stack ingests are listed

**Tests**: REQUIRED, written first, each watched failing for the stated reason. Python tests carry
`@pytest.mark.trace("REQ-WP-081")`; the page test carries `// @trace: REQ-WP-081`.

## Phase 1: Setup

- [x] T001 Record the **before**: `GET /api/v1/markets` on the running stack (`{"markets":[]}`), and that nothing under `src/` calls `add_market` outside tests

## Phase 2: Tests first

- [x] T002 [US2] Write `tests/unit/connectors/test_market_types.py` (pytest): every venue in `VENUE_REGISTRY` has a market type (SC-004); the type agrees with the endpoint the daemon really uses — `binance_stream_url` is the spot host so binance is `spot`, the Bybit URL ends `/linear` so bybit is `perp`, OKX reads the suffix (`BTC-USDT-SWAP` perp, `BTC-USDT` spot, `BTC-USDT-240329` refused) — and a table of endpoint markers fails the test if an endpoint implies a type the registry does not give (D3)
- [x] T003 [US3] Write `tests/unit/pipeline/test_market_registration.py` (pytest, a real SQLite catalog): `unruled_market_row` is exactly what `LakehouseRepository.add_market` writes without rules; registering writes one row that reads back with **no instrument**; registering twice and ten times leaves one row for the key; a key held **with** trading rules is recognised and not overwritten; five keys registered from five threads end with five rows; through `ingest_main.main` (with `build_daemon` replaced by a fake whose `run` is recorded): a failing registration logs **one** WARNING naming venue and symbol, `run` is still called, and registration is attempted **once** (no loop, FR-006); an unrecognised OKX instrument does the same
- [x] T004 [P] [US1] Write `apps/web/src/__tests__/marketsFiveRows.test.tsx` (vitest): the real response shape for the five markets (nulls for the scores) renders five rows, each a link to its chart at the chosen timeframe, showing `venue · market_type`
- [x] T005 Run T002–T004 and record the RED output in the implement outcome note. Do not commit while red

## Phase 3: Implementation

- [x] T006 Add `market_type: Callable[[str], str]` to `VenueConfig` and the three entries in `src/channelflow/connectors/venue.py` (binance `spot`, with the reason beside it; bybit `perp`; OKX by suffix, refusing an unknown form); add `unruled_market_row` to `src/channelflow/tables/features.py` and make `add_market` use it; write `src/channelflow/pipeline/market_registration.py` (`register_market`, idempotent by reading first, and `register_softly`); call it in `ingest_main.main` before `daemon.run()`. `# @trace: REQ-WP-081` in each
- [x] T007 Run the new tests and the existing repository, API, pipeline and ingest tests: the existing ones pass **unchanged**
- [x] T008 [P] ~~Write `tests/integration/test_market_registration.py` (the five threads against the stack's PostgreSQL catalog)~~ **not written, deliberately**: the markets table has a fixed name and the stack's catalog is the live one, so the test would write into the list the API serves. The five-thread and the deterministic-interleaving tests on SQLite carry it. Written: a section in `docs/deployment.md`: the markets are registered by each ingest service; the types and why Binance is spot; that no rules are registered
- [x] T009 First run `tests/tools/test_mutate.py`. Then write `tests/mutations/market_registration.toml`: the type constant changed; OKX treating every instrument as `perp`; registering without reading first; overwriting a held key; a registration failure raised out of `main`; a retry loop; the venue registry entry lacking its type. **A survivor needs a test that kills it or a written reason**
- [x] T010 `make lint`, `make typecheck`, `make test`, `make web-typecheck`, `make web-test`, `make web-build`

## Phase 4: Live

- [x] T011 Deploy the five ingest services only (`docker compose up -d --build --no-deps …`): each loses up to fifteen buffered bars, the documented trade, and `worker` and `resample` are untouched so the [[REQ-WP-079]] measurement is undisturbed. Record, with the date, `GET /api/v1/markets` (five entries, binance spot, bybit and okx perp), then restart one daemon twice and show the list still has five
- [x] T012 Write the implement outcome note; set `implemented` (the live acceptance is satisfied by T011); `make graph && make validate`; commit through the gate naming explicit paths

## Coverage

| requirement | task |
|---|---|
| FR-001 each process registers | T003, T006, T011 |
| FR-002 row has the registry's type, no rules | T003, T006 |
| FR-003 every venue names a type, only in the registry | T002, T006 |
| FR-004 binance spot, tied to the endpoint | T002 |
| FR-005 registering a present key adds nothing | T003 |
| FR-006 soft failure, no loop | T003 |
| FR-007 the overview shows a row per market | T004 |
| SC-001 five entries on the running stack | T011 |
| SC-002 ten starts, one row | T003 |
| SC-003 bars unchanged with registration failing | T003 (`run` still called) |
| SC-004 no venue lacks a type | T002 |

## Dependencies & Execution Order

T001 first; T002, T003, T004 together, then T005; T006 → T007; T008 and T009 after T007; T010 after those;
T011 after T010; T012 last.
