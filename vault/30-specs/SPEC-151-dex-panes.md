---
id: SPEC-151-dex-panes
requirement: REQ-WP-099
speckit_path: specs/151-dex-panes/spec.md
status: draft
---

## Summary

Collect the two busiest WHYPE/USDC pools on HyperEVM through the public node (swaps and `liquidity()`), ingest Bybit
`HYPEUSDT` as the series that carries them, and have the worker write `dex_swap_imbalance` and `dex_active_liquidity` for it
as of each bar's close.

## Links

- Requirement: [[REQ-WP-099]]
- Builds on: [[REQ-WP-058]], [[REQ-WP-059]], [[REQ-WP-063]]
