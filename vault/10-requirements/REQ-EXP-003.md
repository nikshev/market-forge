---
id: REQ-EXP-003
title: Rejection detector
type: experiment
prd_ref: "EXP-003 Rejection detector"
prd_lines: "5083-5091"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Compare:

- wick only;
- close-back-inside;
- two-bar confirmation;
- order-flow confirmation.

## Acceptance

- all four detectors — wick only, close-back-inside, two-bar confirmation,
  order-flow confirmation — appear in the report;
- each detector used is a production `RejectionDetector` driven by the signal
  machine, never a copy of its logic (PRD §25.2);
- a detector whose inputs do not exist is reported as unavailable with the
  reason, and is not scored;
- for each detector, over identical bars and one split: confirmation count,
  median confirmation lag in bars, the share of confirmations later invalidated,
  and expectancy in R after costs out of sample;
- the ranking is by a declared rule, and the report states that a detector may
  win on lag and lose on expectancy;
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
