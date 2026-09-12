---
id: REQ-PHASE-4
title: DeFi ingestion + AMM market structure
type: phase
prd_ref: "Phase 4 — DeFi ingestion + AMM market structure"
prd_lines: "6776-6820"
phase: 4
status: planned
depends_on: ["REQ-PHASE-3"]
tags: []
covers: [REQ-WP-014, REQ-WP-015, REQ-WP-045, REQ-WP-046, REQ-ASSET-001, REQ-BIAS-006, REQ-EXP-007]
not_delivered:
  - "Curve twocrypto quoting: [[REQ-WP-046]] classifies it and quotes Stableswap-NG and tricrypto; the deployed twocrypto version has no matching published source"
  - "Uniswap v4 PoolManager adapter and hook safety classification: not built"
  - "HyperCore CLOB adapter and HyperEVM ingestion profile: not built"
  - "Iceberg canonical DeFi tables: the plane is Iceberg since [[REQ-WP-039]], and no DeFi table is defined on it"
  - "Pinot HOT DeFi datasets: deferred by ADR-002 until a HOT serving requirement exists, not missing by oversight"
  - "UI liquidity/depth overlay: the web app has no DEX overlay"
---

## Requirement

Deliverables:

- multi-provider EVM RPC abstraction;
- live head follower + historical backfill;
- raw block/log/receipt canonical persistence;
- reorg/finality manager;
- pool/protocol discovery registry;
- ABI/decoder registry;
- Uniswap v3 pool reducer;
- concentrated-liquidity tick map and depth ±bps;
- Aerodrome Slipstream adapter using shared CL kernel;
- Aerodrome v2 stable/volatile adapter;
- Curve Stableswap-NG/Cryptoswap quote/depth adapter;
- Uniswap v4 PoolManager/PoolId adapter;
- v4 hook/custom-accounting safety classification;
- HyperCore native CLOB adapter (`l2Book`, trades, mids, asset contexts);
- HyperEVM EVM-ingestion profile;
- normalized swaps/liquidity/depth model;
- asset identity registry;
- CEX↔DEX executable-price normalization;
- DEX swap imbalance;
- LP liquidity delta/migration;
- executable DEX-CEX basis after estimated fees/gas/impact;
- Pinot HOT DeFi datasets;
- Iceberg canonical DeFi tables;
- UI liquidity/depth overlay.

Acceptance:

- reproduce known Uniswap v3 pool price from sqrtPrice/tick;
- deterministic checkpoint + replay reconstruction fixture;
- tick crossing updates active liquidity correctly;
- forced log gap disables stateful features until repaired;
- reorg fixture rolls state back and emits correction/invalidation;
- compute ETH/USDC DEX depth around market price for ±10/25/50/100 bps;
- Curve quote curve agrees with a trusted point-in-time contract quote within configured tolerance;
- Uniswap v4 PoolId resolves to the correct PoolKey and hook classification;
- unsupported v4 custom-accounting pool fails closed instead of emitting fake CL depth;
- Aerodrome v2 and Slipstream are decoded as distinct AMM models;
- HyperCore reconnect restores current book snapshot without treating it as AMM liquidity;
- CEX top-of-book is never compared directly with DEX infinitesimal spot for arbitrage scoring;
- backtest uses `available_at` and selected finality policy, not only block timestamp.

## Acceptance

- reproduce known Uniswap v3 pool price from sqrtPrice/tick;
- deterministic checkpoint + replay reconstruction fixture;
- tick crossing updates active liquidity correctly;
- forced log gap disables stateful features until repaired;
- reorg fixture rolls state back and emits correction/invalidation;
- compute ETH/USDC DEX depth around market price for ±10/25/50/100 bps;
- Curve quote curve agrees with a trusted point-in-time contract quote within configured tolerance;
- Uniswap v4 PoolId resolves to the correct PoolKey and hook classification;
- unsupported v4 custom-accounting pool fails closed instead of emitting fake CL depth;
- Aerodrome v2 and Slipstream are decoded as distinct AMM models;
- HyperCore reconnect restores current book snapshot without treating it as AMM liquidity;
- CEX top-of-book is never compared directly with DEX infinitesimal spot for arbitrage scoring;
- backtest uses `available_at` and selected finality policy, not only block timestamp.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-014]]
- [[REQ-WP-015]]
- [[REQ-ASSET-001]]
- [[REQ-BIAS-006]]
- [[REQ-EXP-007]]

**Not delivered:**

- Aerodrome Slipstream and v2 adapters: not built
- Curve Stableswap-NG/Cryptoswap adapter: not built
- Uniswap v4 PoolManager adapter and hook safety classification: not built
- HyperCore CLOB adapter and HyperEVM ingestion profile: not built
- Iceberg canonical DeFi tables: no Parquet/Iceberg plane exists; the API reads from an in-memory repository ([[ADR-019]])
- Pinot HOT DeFi datasets: deferred by [[ADR-002]] until a HOT serving requirement exists, not missing by oversight
- UI liquidity/depth overlay: the web app has no DEX overlay

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_4_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

**Corrected 2026-09-11.** The Iceberg entry said "no Parquet/Iceberg plane
exists". That stopped being true when [[REQ-WP-039]] landed, and a `not_delivered`
line that overstates what is missing is as misleading as one that understates
it: somebody reading this to plan Phase 4 would have budgeted for building a
plane that is already there. What remains undelivered is narrower and is what
the line now says — the plane exists and no DeFi table is defined on it.
