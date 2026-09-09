---
id: REQ-EXP-004
title: OFI incremental value
type: experiment
prd_ref: "EXP-004 OFI incremental value"
prd_lines: "5092-5101"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Ablation:

- channel only;
- +L1 imbalance;
- +multi-level imbalance;
- +OFI;
- +persistence/cancellation.

## Acceptance

- the five arms appear and are cumulative as the PRD lists them: each contains
  the previous arm's features;
- an arm whose family contributes no feature is reported as not run, with the
  reason, and never scored;
- every arm is fitted and scored on one fold set and one target;
- the report states what each family added over the arm before it, not only each
  arm's absolute score;
- one input produces one report.

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
