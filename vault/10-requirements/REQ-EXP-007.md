---
id: REQ-EXP-007
title: DEX incremental value
type: experiment
prd_ref: "EXP-007 DEX incremental value"
prd_lines: "5117-5126"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

For ETH:

- CEX only;
- CEX + DEX price divergence;
- + DEX depth asymmetry;
- + swap imbalance;
- + LP liquidity changes.

## Acceptance

- the five arms appear and are cumulative: CEX only; + DEX price divergence;
  + DEX depth asymmetry; + swap imbalance; + LP liquidity changes;
- an arm whose family contributes no feature is reported as not run, with the
  reason, and never scored;
- every arm is fitted and scored on one fold set;
- the report states the instrument it was run on, because EXP-007 names one
  (ETH).

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
