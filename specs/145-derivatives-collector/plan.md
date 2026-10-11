# Implementation Plan: The derivatives panes are fed by a collector

**Branch**: `145-derivatives-collector` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/145-derivatives-collector/spec.md`; architecture in [[ADR-070]]. Specs 146 (liquidations) and 147 (book) add streams to the **same** service and reuse its runtime, so what is shared is built here.

## Summary

A new package `channelflow.context` holds the shared collector runtime and the REST pollers; a new entrypoint `pipeline/context_main.py` composes it per venue; a new table `derivatives_state` stores the output; the worker gains one pass, `write_context_features`, called beside `write_flow_features`, that evaluates the three features at every bar close. Compose gets three services (`context-binance`, `context-bybit`, `context-okx`) started with `--no-deps`; the worker is rebuilt last, after a no-write replay on the real lakehouse.

## Technical Context

**Language/Version**: Python 3.12. **Dependencies**: `httpx` (already a dependency; the notary uses it), `websockets` (already; specs 146/147). No new package.

**Storage**: Iceberg through the existing `lakehouse` layer; sinks buffered like `BarSink`/`DexSwapSink` (a commit per flush interval, not per row).

**Testing**: pytest, no network. REST behind a `Fetch` callable the tests replace with recorded responses (kept under `tests/fixtures/context/`, recorded 2026-10-11 from the three venues by a small capture script like `tools/record/*`). The worker pass is tested against an in-memory features table.

**Constraints**: no existing container is recreated by the collectors' start; the worker is rebuilt only after the pass has been replayed against the real lakehouse without writing (lesson of 2026-10-08); host load measured (SC-006).

**Scale/Scope**: 5 series, 3 collectors, ~3 REST calls/min/symbol, ~7 tables' worth of rows per day at 1/min -- small; the cost is in the worker backfill (below).

## Constitution Check

| Principle | Status |
|---|---|
| I. No look-ahead | **Engaged.** Value at a close = states with `event_time <= close`; funding uses `settled_funding`; tested by appending later rows (SC-002). |
| II. Event time vs receive time | **Engaged.** Both stored, never swapped (FR-003). |
| III-X | Staleness explicit per feature (X: parameters configurable and named). |
| XI. Reproducible | Fixtures recorded; the worker pass is a pure function of stored rows. |
| XII. Correctness before performance | The backfill is made fast by bisecting sorted states, not by changing what is computed. |
| XIII. Incremental | Spec 145 first; 146/147 add streams. |
| XIV. Traceable | `# @trace: REQ-WP-093` on every new file; tests marked. |

## Project Structure

```text
src/channelflow/context/
├── __init__.py
├── sources.py        # the one place a series is tied to its venue's perpetual (FR-012) and each venue's endpoints, cadence, staleness
├── rest.py           # Fetch protocol, httpx implementation with timeout, status/limit handling, backoff
├── pollers.py        # per venue: poll(symbol) -> DerivativesState | None; history(symbol) -> [DerivativesState]
├── runtime.py        # the collector loop: cadence, flush, heartbeat, reconnect hooks for 146/147, shutdown
└── status.py         # health + /metrics (the notary's tiny server pattern)
src/channelflow/tables/derivatives_state.py   # schema, to_row/from_row, DerivativesStateSink, table_for
src/channelflow/features/context_write.py     # write_context_features(): the worker's pass; as-of evaluation with bisect
src/channelflow/pipeline/context_main.py      # composition root, like ingest_main
tools/record/derivatives_capture.py           # one-shot recorder of the REST fixtures
tests/unit/context/…  tests/unit/tables/test_derivatives_state.py  tests/unit/features/test_context_write.py
tests/mutations/context_*.toml
```

Touched: `connectors/{binance,bybit,okx}/normalize.py` (`derivatives_state` gains the USD figures and the history rows), `pipeline/channel_main.py` (one call), `pipeline/maintenance_main.py` (TABLES), `docker-compose.yml` (3 services), `deploy/prometheus/prometheus.yml` (targets), `docs/deployment.md`, `.env.example`.

## Design decisions, with what was rejected

1. **Poll REST, not websocket.** Mark/index/funding have streams, but open interest USD and funding history only exist on REST for Binance; one mechanism for all three venues. Rejected: a mixed WS+REST design (two failure modes for no extra data at a one-minute cadence).
2. **Binance open interest USD from `openInterestHist` (5 m buckets)**, event time = the bucket's timestamp, deduplicated by it. Rejected: `openInterest × markPrice` (a price of our choosing; `oi_series` skips such states on purpose).
3. **One state row per poll**, joining the REST answers of that venue into one `DerivativesState`; a poll in which a required answer failed stores nothing (FR-004) rather than a half-state.
4. **Staleness constants live in `context/sources.py`**, each with its reason: polled values 3 poll intervals (3 min); Binance USD OI 15 min (a 5-minute bucket that lands up to ~5 min late, plus slack); funding settlement `interval + 1 h` from the venue's reported interval (Bybit `fundingIntervalHour`, OKX `fundingTime - prevFundingTime`, Binance `fundingInfo`/8 h default).
5. **History is the funding series, loaded at start and refreshed hourly; polled states never enter `funding_z`.** `settled_funding` returns every state whose `next_funding_time` has passed -- one per poll, not one per settlement -- so a window of 24 over polled states would be 24 estimates of one interval. The writer filters to `history` rows (one per settlement, the venue's settled rate) before calling the library. Rows tagged `history`, `event_time = settlement time`, `next_funding_time = settlement time`, no mark/index/OI. Idempotent by identity. Binance `fundingRate` (limit 1000), Bybit `funding/history` (200), OKX `funding-rate-history` (100): 24 settlements need ≤ 8 days and all three return that.
6. **The worker evaluates each feature per bar with `bisect` over states sorted by event time**, passing the library the slice at or before the close (`states[:i]`), so the library's own guards still apply and the cost is O(log n) per bar plus the slice the function needs. Rejected: re-implementing the maths in the writer (two truths).
7. **Per-feature watermark** (latest `at_ns` per series, timeframe and feature in `feature_snapshots`), one table read per pass as `latest_flow_times` does (ADR-056). A bar is written only if its value exists; absent bars are re-evaluated next pass and cost nothing but the evaluation.
8. **Status server**: `/healthz` (200 only when the newest successful poll is within 3 intervals and, for sockets, the stream is alive) and `/metrics` with `context_last_state_age_seconds{venue}`, `context_poll_failures_total{venue,endpoint}`; compose healthcheck calls `/healthz`; Prometheus scrapes it.

## Risks

- **Rate limits / IP bans** on public endpoints: ~3 calls/min/symbol is far below published limits; 429 and 418 back off for the `Retry-After` or a stated minimum and store nothing.
- **Worker backfill time** on the first pass: measured in the no-write replay before the rebuild; if long, the pass processes timeframes in order and is bounded per pass (it resumes by watermark).
- **Iceberg small files**: sinks buffer (flush every 5 minutes or 50 rows); the maintenance service compacts.
- **A venue changes a response shape**: the normalizer refuses with the field named (`_require`), the poll stores nothing, the failure counter rises and health fails -- visible, not silent.

## Phases

1. Fixtures, normalizers, table, sink (tests first). 2. Pollers + history + runtime + status + entrypoint. 3. Worker pass + replay against the real lakehouse, no write. 4. Compose, docs, Prometheus. 5. Deploy collectors (`up -d --no-deps`), let them run, then rebuild the worker, then SC-001/SC-005/SC-006.
