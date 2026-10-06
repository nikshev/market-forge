# Research: Cross-venue Consensus

## R1. Quote ingestion — how to get mids

The `crossvenue.consensus_mid` function needs `quotes` — a list of `{venue, mid, ts}` per venue. Currently the ingest reads trades only. Book subscription (Binance `bookTicker`, Bybit/OKX tickers) is the source of mids. This is [[REQ-WP-011]]'s work and is the same data OFI/depth-imbalance need.

**Decision**: New ingest service per venue (`ingest-quotes-<venue>`) subscribes to book ticker, computes mid = (bid+ask)/2, writes to `quotes` table. Same pattern as trade ingest: one symbol per process, one venue per process. The `quotes` table schema mirrors trade ingest but with bid/ask/mid instead of price/volume.

## R2. Consensus computation — when and how

The PRD says consensus at each bar's close from fresh mids. `consensus_mid(quotes, registry, at_ns, staleness_ns)` already enforces:
- Quote `ts ≤ at_ns` (no look-ahead)
- Quote not stale (`at_ns - ts ≤ staleness_ns`)
- ≥2 venues for one asset, or refusal

**Decision**: Consensus worker runs every 5 min (`CHANNELFLOW_CONSENSUS_INTERVAL`, same as channel pass). For each bar that closed since last pass, it reads quotes at `bar_close_ns`, calls `consensus_mid`, writes `ConsensusMid` row per market type. If <2 venues, writes row with `refusal_reason`.

## R3. Venue basis — computation and feature name

`basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)`. The viewed venue's mid at bar close vs its market-type's consensus.

**Decision**: 
- Feature name `venue_basis_bps` (not `basis_bps`) to avoid collision with derivatives basis.
- Registered as `FeatureSpec` with unit=bps, cadence=bar close, source=cross-venue consensus.
- Computed in API from consensus rows + viewed venue's quote at bar close.

## R4. Mixed instrument types — spot vs perp

Binance spot, Bybit/OKX perps. A median over spot mid + perp mids blends spot-perp basis into consensus.

**Decision**: Consensus **per market type** (registry provides type per venue). Spot venues together, perp venues together. Viewed venue's basis uses its type's consensus. This is explicit in FR-006 and SC-005 with a test pinning it.

## R5. API endpoints

Two new endpoints:
1. `GET /api/v1/consensus` — per-bar consensus mids for window (4h/24h/7d), with venue count and refusal reasons.
2. `GET /api/v1/features/timeseries?feature=venue_basis_bps` — viewed venue's basis to consensus.

Both respect `at_ns` (point-in-time for AS-SEEN-THEN) and `as_of_ns` (no look-ahead for CURRENT REFIT).

## R6. Web — chart layer and pane

- Consensus line: optional chart layer (off by default), drawn as line series at bar close times with consensus mid price. Gaps where <2 venues; notice at gaps.
- Venue basis pane: lower pane, line series like CVD, aligned to bars, shows `venue_basis_bps`.

## R7. Configuration

- `CHANNELFLOW_CONSENSUS_INTERVAL` — worker interval (default 5m, same as channel)
- `CHANNELFLOW_CONSENSUS_STALENESS_NS` — quote staleness window (default 60s)
- Window sizes: 4h, 24h, 7d (same as volume profile)