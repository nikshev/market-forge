# Implementation Plan: Cross-venue consensus mid and venue basis

**Branch**: `140-cross-venue-consensus` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/140-cross-venue-consensus/spec.md`

## Summary

Two deliverables: (1) consensus mid line on chart (optional layer), (2) venue basis pane (`venue_basis_bps`). Both consume top-of-book quotes from ≥2 venues per market type, computed at each bar's close via `crossvenue.consensus_mid` (already enforces no look-ahead). Book subscription ([[REQ-WP-011]]) must land first — this plan assumes quotes exist. Mixed instrument types handled by consensus per market type (spot/perp).

## Technical Context

**Language/Version**: Python 3.12 (API, pipeline), TypeScript 5.6 (web)

**Primary Dependencies**: 
- `crossvenue` library ([[REQ-WP-016]]) — `consensus_mid`, `basis_bps`
- `instrument_metadata` ([[REQ-WP-060]]) — registry maps venues to assets and market types
- Book subscription ([[REQ-WP-011]]) — provides top-of-book quotes (Binance `bookTicker`, Bybit/OKX tickers)
- Existing API (`src/channelflow/api/`) and web (`apps/web/src/`)

**Storage**: PostgreSQL (quotes table, new), Iceberg lakehouse (bars, features)

**Testing**: pytest (API, pipeline), vitest (web), traceability markers

**Target Platform**: Linux containers (Docker compose)

**Project Type**: Web application + data pipeline

**Performance Goals**: Consensus computed at bar close (5-min channel interval); API serves 4h/24h/7d windows

**Constraints**: 
- Principle I: No look-ahead — consensus at `t` uses only quotes ≤ `t`
- Principle III: History immutable — committed consensus never rewritten
- Principle VII: Live = replay — same computation code
- Principle X: Thresholds configurable — staleness window, window sizes
- FR-016: Failed loads stated, never blank
- `basis_bps` name collision with derivatives basis — use `venue_basis_bps`

**Scale/Scope**: 3 venues (Binance spot, Bybit perp, OKX perp), 1 asset (BTCUSDT/ETHUSDT/SOLUSDT), per-bar consensus

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. No look-ahead | Pass | `consensus_mid` called at bar close with quotes ≤ instant; API respects `at_ns`/`as_of_ns` |
| II. Time is not one thing | Pass | Quote timestamps distinct from bar timestamps; `event_time` on quotes |
| III. History immutable | Pass | Consensus per bar never rewritten; pipeline appends |
| IV. Baselines before models | N/A | Deterministic median |
| V. Calibration, not accuracy | N/A | Not probabilistic |
| VI. Every feature documented | Pass | `venue_basis_bps` registered with `FeatureSpec` |
| VII. Live and replay same code | Pass | Same `consensus_mid` call in pipeline and API |
| VIII. Connectors share one interface | Pass | Book subscription uses common interface |
| IX. No automatic execution | N/A | Analytics only |
| X. Thresholds are configuration | Pass | Staleness, windows configurable |
| XI. Results reproducible | Pass | Dataset version, config hash, commit hash |
| XII. Correctness precedes performance | Pass | Median is O(n) |
| XIII. Work incremental | Pass | Book sub first, then this |
| XIV. Everything traceable | Pass | Spec has `traces: [REQ-WP-091]` |

No violations.

## Project Structure

### Documentation (this feature)

```text
specs/140-cross-venue-consensus/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
src/channelflow/
├── crossvenue/              # existing library (consensus_mid, basis_bps)
├── pipeline/
│   ├── ingest_quotes.py     # NEW: book subscription → quotes table
│   ├── consensus_pass.py    # NEW: compute consensus per bar, write to lakehouse
│   └── consensus_main.py    # NEW: entrypoint for consensus worker
├── api/
│   ├── routes.py            # ADD: /consensus, /features/timeseries (venue_basis_bps)
│   ├── repositories.py      # ADD: consensus queries
│   └── schemas.py           # ADD: ConsensusOut, VenueBasisOut
├── features/
│   └── crossvenue_basis.py  # NEW: venue_basis_bps FeatureSpec + computation
├── tables/
│   └── quotes.py            # NEW: quotes table schema
└── tables/
    └── consensus.py         # NEW: consensus table schema

apps/web/src/
├── api.ts                   # ADD: fetchConsensus, fetchVenueBasis
├── Chart.tsx                # ADD: consensus line layer
├── types.ts                 # ADD: ConsensusOut, VenueBasisOut
├── panes.ts                 # ADD: venue_basis_bps to pane list
└── __tests__/
    ├── consensus.test.tsx
    └── venueBasis.test.tsx
```

## Phase 0: Research

No NEEDS CLARIFICATION markers. Research records decisions:

- **Quote ingestion**: New ingest service per venue subscribes to book ticker, writes quotes to `quotes` table (venue, symbol, bid, ask, mid, ts). Same pattern as trade ingest.
- **Consensus pass**: Worker runs every 5 min (`CHANNELFLOW_CONSENSUS_INTERVAL`), reads quotes at each bar close, calls `consensus_mid`, writes consensus rows.
- **API**: Two new endpoints — `/api/v1/consensus` (per-bar consensus mids), `/api/v1/features/timeseries` with `feature=venue_basis_bps`.
- **Web**: Consensus line as chart layer (like channel); basis pane as line series (like CVD).
- **Mixed types**: Registry provides market type per venue; consensus computed per type; viewed venue uses its type's consensus.

## Phase 1: Design & Contracts

### data-model.md

```markdown
# Data Model: Cross-venue Consensus

## Entities

### Quote
- `venue: str` — exchange (binance, bybit, okx)
- `symbol: str` — e.g., BTCUSDT
- `bid: Decimal` — best bid
- `ask: Decimal` — best ask
- `mid: Decimal` — (bid + ask) / 2
- `ts_ns: int` — quote timestamp (exchange_time)
- `ingest_ns: int` — when we received it

### ConsensusMid
- `asset: str` — e.g., BTCUSDT
- `market_type: str` — spot | perp
- `bar_close_ns: int` — bar close time
- `consensus_mid: Decimal` — median of fresh mids
- `venue_count: int` — number of contributing venues
- `refusal_reason: str | null` — why <2 venues (stale, future, none)

### VenueBasisPoint
- `asset: str`
- `market_type: str`
- `venue: str` — viewed venue
- `bar_close_ns: int`
- `venue_basis_bps: Decimal` — 10000 * (mid_i / consensus_mid - 1)
```

### contracts/api-contract.md

```markdown
# API Contracts: Cross-venue Consensus

## GET /api/v1/consensus
Query: `venue`, `symbol`, `timeframe_ns`, `window` (4h|24h|7d), `at_ns` (optional)
Response: `{ consensus: ConsensusMid[], window, at_ns }`

## GET /api/v1/features/timeseries
Query: `venue`, `symbol`, `timeframe_ns`, `feature=venue_basis_bps`, `start_ns`, `end_ns`
Response: `{ points: VenueBasisPoint[] }`
```

### quickstart.md

```markdown
# Quickstart: Cross-venue Consensus

## Prerequisites
- Running stack with book subscription ([[REQ-WP-011]]) delivering quotes
- Instrument registry populated with market types

## Validation
1. Call `/api/v1/consensus?venue=binance&symbol=BTCUSDT&timeframe_ns=900000000000&window=24h`
   - Returns per-bar consensus mids with venue counts
2. Call `/api/v1/features/timeseries?feature=venue_basis_bps&...`
   - Returns basis points for viewed venue
3. Open chart with consensus layer on — line at bar consensus mids
4. Open basis pane — shows `venue_basis_bps` line
5. Screenshots light/dark under `docs/ui/`
```