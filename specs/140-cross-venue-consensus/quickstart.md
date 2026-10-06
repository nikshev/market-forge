# Quickstart: Cross-venue Consensus

## Prerequisites

- Running stack with book subscription ([[REQ-WP-011]]) delivering quotes to `quotes` table
- Instrument registry ([[REQ-WP-060]]) populated with market types per venue
- Consensus worker running (`docker compose up -d consensus-worker`)

## Validation Scenarios

### 1. Consensus library correctness (unit)
```bash
.venv/bin/python -m pytest tests/unit/crossvenue/test_consensus.py -v
```
Fixtures: 2 venues → median; 3 venues → median; stale quote excluded; future quote excluded; one venue refuses.

### 2. API serves consensus
```bash
curl "http://localhost:8000/api/v1/consensus?venue=binance&symbol=BTCUSDT&timeframe_ns=900000000000&window=24h"
```
Returns: `{ consensus: [...], window: "24h", at_ns: "..." }` — each entry has `bar_close_ns`, `consensus_mid`, `venue_count`, `refusal_reason?`.

### 3. API serves venue basis
```bash
curl "http://localhost:8000/api/v1/features/timeseries?venue=binance&symbol=BTCUSDT&timeframe_ns=900000000000&feature=venue_basis_bps&start_ns=...&end_ns=..."
```
Returns: `{ points: [{bar_close_ns, venue_basis_bps}, ...] }`

### 4. Chart with consensus layer
Open `http://localhost:8080/chart/binance/BTCUSDT?tf=15m&overlays=consensus`
- Consensus line drawn at bar consensus mids (where ≥2 venues)
- Gaps where <2 venues; notice at gaps

### 5. Basis pane
Lower pane selector → `venue_basis_bps` → line series at bar basis points

### 6. Mixed types test
```bash
.venv/bin/python -m pytest tests/unit/crossvenue/test_mixed_types.py -v
```
Fixture: Binance spot + Bybit/OKX perps → spot consensus from Binance only (refused, <2); perp consensus from Bybit+OKX; Binance basis uses spot consensus (refused), Bybit basis uses perp consensus.

### 7. Screenshots
Light/dark chart with consensus line and basis pane → `docs/ui/consensus-{light,dark}.png`, `docs/ui/basis-{light,dark}.png`