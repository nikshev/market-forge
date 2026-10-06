# Data Model: Cross-venue Consensus

## Entities

### Quote
- `venue: str` — exchange (binance, bybit, okx)
- `symbol: str` — e.g., BTCUSDT
- `bid: Decimal` — best bid price
- `ask: Decimal` — best ask price
- `mid: Decimal` — (bid + ask) / 2
- `ts_ns: int` — quote timestamp (exchange_time)
- `ingest_ns: int` — when we received it

### ConsensusMid
- `asset: str` — e.g., BTCUSDT
- `market_type: str` — spot | perp
- `bar_close_ns: int` — bar close time
- `consensus_mid: Decimal` — median of fresh mids
- `venue_count: int` — number of contributing venues (≥2, else 0)
- `refusal_reason: str | null` — why <2 venues: "stale", "future", "one_venue", "no_quotes"

### VenueBasisPoint
- `asset: str`
- `market_type: str`
- `venue: str` — viewed venue
- `bar_close_ns: int`
- `venue_basis_bps: Decimal` — 10000 * (mid_i / consensus_mid - 1)

## State Transitions

Quote: received → written to quotes table (append-only)
ConsensusMid: bar closes → worker reads quotes at bar_close_ns → computes → writes (append-only, never rewritten)
VenueBasisPoint: API computes on request from ConsensusMid + viewed venue's quote at bar_close_ns