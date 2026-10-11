---
id: SPEC-150-second-spot-venue
requirement: REQ-WP-098
speckit_path: specs/150-second-spot-venue/spec.md
status: draft
---

## Summary

Ingest OKX spot BTC/ETH/SOL-USDT, collect their books (spot sizes are base units, a swap's are contracts), map each to its
pair's perpetual, and list them in the consensus registry so the Binance spot venue-basis pane has a line.

## Links

- Requirement: [[REQ-WP-098]]
- Decision: [[ADR-070]]
