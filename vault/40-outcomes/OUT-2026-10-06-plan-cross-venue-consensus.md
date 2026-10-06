---
id: OUT-2026-10-06-plan-cross-venue-consensus
step: plan
records: [REQ-WP-091]
commit: null
---

## What was decided

- **Two deliverables in sequence**: book subscription ([[REQ-WP-011]]) first, then this. This plan assumes quotes exist.
- **Consensus per market type** (spot/perp) — avoids blending spot-perp basis. Explicit in FR-006 with test.
- **Feature name `venue_basis_bps`** — avoids collision with derivatives `basis_bps`.
- **Library reuse**: `crossvenue.consensus_mid` already enforces no look-ahead; called at bar close.
- **Two API endpoints**: `/consensus` (per-bar mids with venue count/refusal) and `/features/timeseries?feature=venue_basis_bps`.
- **Chart layer** (optional, off by default) + **lower pane** (line series like CVD).
- **Config**: `CHANNELFLOW_CONSENSUS_INTERVAL` (5m), `CHANNELFLOW_CONSENSUS_STALENESS_NS` (60s).
- **Tables**: `quotes` (bid/ask/mid/ts), `consensus` (per market type per bar).
- **No DeFi in consensus** — per PRD §17.1.

## What is still open

- Book subscription ([[REQ-WP-011]]) must land first.
- Mixed-type test fixture design.
- Live screenshots after book data exists.