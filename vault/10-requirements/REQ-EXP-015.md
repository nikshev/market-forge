---
id: REQ-EXP-015
title: Derivatives/DeFi confluence at turning points
type: experiment
prd_ref: "EXP-015 Derivatives/DeFi confluence at turning points"
prd_lines: "5229-5240"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

For BTC/ETH and other liquid assets, test whether turning-point probability improves from:

- OI/funding/liquidations;
- DEX-CEX executable basis;
- DEX depth asymmetry;
- swap imbalance;
- LP liquidity migration.

Use strict ablation and same walk-forward folds.

## Acceptance

- the ablation is strict (one factor at a time) and uses the same walk-forward folds across OI/funding/liquidations, DEX-CEX executable basis, DEX depth asymmetry, swap imbalance, and LP liquidity migration variants.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
