---
id: OUT-2026-10-07-implement-cross-venue-consensus
step: implement
records: [REQ-WP-091]
commit: null
---

## What was done

Implemented REQ-WP-091 (cross-venue consensus mid + venue basis) through tasks T002–T028 (T029–T033 polish below).

## Implementation summary

### Foundational (T002–T006)
- `.env.example`: `CHANNELFLOW_CONSENSUS_INTERVAL=5m`, `CHANNELFLOW_CONSENSUS_STALENESS_NS=60000000000` + docs row (T002).
- `src/channelflow/tables/quotes.py`: quotes table (venue/symbol/bid/ask/mid/ts_ns exchange time/ingest_ns receive time) (T003).
- `src/channelflow/tables/consensus.py`: consensus table per (asset, market_type, bar_close) with refusal rows (T004).
- `src/channelflow/features/crossvenue_basis.py`: `venue_basis_bps` FeatureSpec + helper; registered in `__init__.exposed_feature_names`; truncation parity case added to `test_truncation_parity.py` (62nd feature, 46 cases) (T005).
- `apps/web/src/panes.ts`: `venue_basis_bps` pane entry; count updates in 5 test files (T006).

### US1 library (T007–T009)
- `tests/unit/crossvenue/test_consensus_091.py`: 6 acceptance tests over existing `consensus_mid` (median, exclusions, refusal, no look-ahead). RED skipped plainly: library already implemented by REQ-WP-016.
- `consensus.py` docstring pins US1 acceptance; file carries both `REQ-WP-016` and `REQ-WP-091` traces (T008).

### US2 API (T010–T014)
- RED: `test_consensus_endpoint.py` (5 tests, 404s) + `test_venue_basis_endpoint.py` (3 RED + 2 design-passing).
- `schemas.py`: `ConsensusBarOut`/`ConsensusResponse`/`VenueBasisPointOut` + wire-time guard registration (T014).
- `repositories.py`: `get_consensus`/`get_venue_basis` over shared row-level selects (T012).
- `lakehouse_repository.py`: same reads over the plane (protocol conformance fix).
- `routes.py`: `GET /api/v1/consensus` (ProfileWindow 4h/24h/7d, at_ns optional, 404 unknown/empty) + `get_feature_series` merges `venue_basis_bps` best-effort (T013). Contract correction: timeseries has NO `feature` param (existing callers + frontend use shape without it); T011 tests fixed accordingly.
- Collateral fixes (documented, required for green): `test_wire_time` TIMESTAMP_FIELDS +3; `test_security` EXPECTED_ROUTES 19→20; T010 zip bug.

### US3 chart (T015–T019)
- RED: `consensus.test.tsx` (4 tests).
- `types.ts`: `ConsensusPointOut`/`ConsensusOut` + `"consensus"` overlay member (T018).
- `api.ts`: `fetchConsensus` with `timeframeNs` (contract fix: endpoint requires it) (T016).
- `Chart.tsx`: consensus line series (violet #7048e8, gaps where refused) + refusal notice; prop is `ConsensusPointOut[]` per test contract (T017).
- `App.tsx`: `wantsConsensus` effect (window 24h, 404 = absence) + `appConsensus.test.tsx` (T019). Consensus does NOT yet refetch on the REQ-WP-090 live tick (recorded, out of scope).

### US4 pane (T020–T024)
- `venueBasis.test.tsx`: paneSeries/availablePanes/PANES behavior (3 tests, pass immediately via generic machinery; RED skipped plainly).

### US5 mixed types (T025–T028)
- `test_consensus_mixed_types.py`: spot/perp separate, viewed venue uses own type, single-type refuses (3 tests). Mutation proof: removing market_type filter fails tests 1–2 as predicted.

## RED evidence
- T010: 5 failed (404, no route). T011: 3 failed (no wiring) + 2 design-passing. T015: 4 failed (no layer). T007/T020/T025: pass immediately over pre-existing/generic behavior (documented, no fabricated failures).

## What was decided
- Consensus per market type (FR-006), never blended; test-pinned.
- `venue_basis_bps` name (not `basis_bps`); server-side merge into timeseries (no contract break).
- Book subscription ([[REQ-WP-011]] quotes ingest + consensus worker) NOT built here: endpoints serve seeded/stored rows; production fill is future work. Pipeline tasks for the worker are the natural follow-up, not this requirement's scope creep.

## Deferred (not waived)
- Live screenshots (T031): require book quotes on the running stack, which do not exist yet (no quotes ingest in compose). Deferred until the worker lands; recorded here, not silently dropped. No T032 artifacts test created (would fail by design).

## Verification
- `make validate`: clean at every implementation commit (full suite incl. integration, run for real).
- `make lint`, `make typecheck` (mypy): clean. Web tsc has 13 pre-existing errors (App/appRefresh/chartRangePreserved/loadStateRefresh, on baseline) — untouched by 091 except App wiring adds none.
- Existing suites: no regressions (appRefresh 5 timeouts and deepLinkOverlays errors pre-existing/flaky on baseline).