---
id: REQ-EXP-012
title: Causal derivative turning points
type: experiment
prd_ref: "EXP-012 Causal derivative turning points"
prd_lines: "5181-5194"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Compare:

- raw trailing return sign change;
- causal local polynomial order 2;
- causal local polynomial order 3;
- Kalman filtered slope;
- one-sided Savitzky-Golay-equivalent implementation if retained.

Evaluate maximum/minimum forecast precision at horizons 3/6/12/24 bars.

Centered filters are allowed only as retrospective label references, never as live candidates.

## Acceptance

_The PRD states no explicit acceptance criteria for this section. They must be written before this requirement leaves `draft`._

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
