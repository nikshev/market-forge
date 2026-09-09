---
id: REQ-EXP-006
title: Derivatives context
type: experiment
prd_ref: "EXP-006 Derivatives context"
prd_lines: "5108-5116"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Analyze conditional outcomes by:

- funding z-score;
- OI change;
- liquidation imbalance;
- basis.

## Acceptance

- outcomes are reported conditionally on each of the four variables: funding
  z-score, OI change, liquidation imbalance, basis;
- each variable is bucketed by a declared rule, and every bucket is reported
  with its count;
- a variable with no data is reported as unavailable, not as a flat conditional;
- every conditional is computed over the same outcomes and the same costs;
- a contemporaneous conditional is labelled as such, so explanatory value around
  an outcome is not read as forecast value (EXP-014's own warning).

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-09. The PRD names what this experiment compares but states no condition
under which it is done. The derivation, what was chosen rather than implied, and
the four criteria every comparison-shaped experiment shares are in
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`.
