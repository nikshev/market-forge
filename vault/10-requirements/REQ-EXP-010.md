---
id: REQ-EXP-010
title: Cross-venue lead/lag
type: experiment
prd_ref: "EXP-010 Cross-venue lead/lag"
prd_lines: "5158-5162"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Measure whether divergence contains predictive value after realistic latency/costs.

## Acceptance

- predictive value is measured out of sample, never in the window the
  correlation was measured on;
- a latency is applied before any divergence is actionable, and it is a required
  parameter rather than zero by default;
- fees and slippage are applied (PRD §41 rule 9);
- the experiment can conclude `NO_EDGE`, and does so when the out-of-sample
  result does not beat the no-skill baseline after latency and costs;
- no module on the signal path imports this experiment, extending ADR-040's
  import ban to it.

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
