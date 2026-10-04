---
id: SPEC-138-volume-profile
requirement: REQ-WP-089
speckit_path: specs/138-volume-profile/spec.md
status: draft
---

## Summary

The ingest aggregates trades per five-minute block and per price bin into buy, sell and unknown base volume (aggressor side only), writing one row per bin
when a block closes and dropping a block whose trade ids show missed trades. A profile for 4h, 24h or 7d is computed on request from the bins as of an
instant, with POC and the value area from the same code the trade-level profile uses, and it states how much of its window the data covers. The chart draws
it with a series primitive at the right edge of the plot, on its own price levels, buy and sell in two colours. Collection starts at deployment; nothing is
backfilled and nothing is inferred from bars.

## Links

- Requirement: [[REQ-WP-089]]
- Built on: [[REQ-WP-012]], [[REQ-WP-083]], [[REQ-WP-092]]
