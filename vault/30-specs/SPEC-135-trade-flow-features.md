---
id: SPEC-135-trade-flow-features
requirement: REQ-WP-088
speckit_path: specs/135-trade-flow-features/spec.md
status: draft
---

## Summary

CVD and the §15.4 trade-imbalance features are derived from the aggressor volumes the bars table already stores
(`aggressive_buy_base`, `aggressive_sell_base`, `delta_base`, trade ids), in base units, by a pure function run in the
worker pass for every timeframe. The sum is kept within a run: a missing bar or, for Binance, a trade-id
discontinuity ends it, and the chart breaks the line there. The unit deviation from PRD §15.4 is recorded in
[[ADR-068]].

## Links

- Requirement: [[REQ-WP-088]]
- Built on: [[REQ-WP-011]], [[REQ-STORE-002]], [[REQ-WP-084]]
- Decision: [[ADR-068]]
