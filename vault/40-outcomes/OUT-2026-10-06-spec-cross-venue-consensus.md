---
id: OUT-2026-10-06-spec-cross-venue-consensus
step: spec
records: [REQ-WP-091]
commit: null
---

## What was done

Read `vault/10-requirements/REQ-WP-091.md` (no `ACCEPTANCE-NOT-SPECIFIED`), constitution, and code facts (`crossvenue` library exists but unused, no mids in ingest, `basis_bps` collision with derivatives basis), then wrote `specs/140-cross-venue-consensus/spec.md` with `traces: [REQ-WP-091]`, checklist, and vault spec note.

## What was decided

- **Two deliverables**: consensus mid line (chart layer) + venue basis pane (lower pane).
- **Consensus per market type**: spot venues together, perp venues together — avoids blending spot-perp basis into consensus. This is explicit in FR-006 and SC-005 with a test pinning it.
- **Library reuse**: `crossvenue.consensus_mid` already enforces no look-ahead; we call it at each bar's close with quotes available then.
- **Book subscription out of scope**: top-of-book quotes needed; separate requirement ([[REQ-WP-011]]) must land first. This requirement assumes quotes exist.
- **Feature name**: `venue_basis_bps` (not `basis_bps`) to avoid collision with derivatives basis.
- **Windows**: 4h, 24h, 7d (same as volume profile).
- **No DeFi in consensus**: per PRD §17.1 "selected high-liquidity venues"; DEX enters lead-lag/executable basis, not price.

## What is still open

- Book subscription ([[REQ-WP-011]]) must land first — this requirement cannot function without quotes.
- Mixed-type rule test needs fixture design (Binance spot + Bybit/OKX perps).
- Live screenshots after book data exists.