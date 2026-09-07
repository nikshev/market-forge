---
id: REQ-EXP-013
title: GMDH derivative extrema
type: experiment
prd_ref: "EXP-013 GMDH derivative extrema"
prd_lines: "5195-5215"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Compare:

- direct classifier only;
- GMDH direct turning-point classifier;
- GMDH forward path + derivative roots;
- ensemble of direct probability + derivative root stability.

Report:

- root presence rate;
- root horizon IQR;
- turn-type agreement;
- time-to-turn MAE;
- extreme-price error;
- calibration;
- incremental expectancy after costs.

Reject the derivative method if roots are unstable or add no OOS value.

## Acceptance

_ACCEPTANCE-NOT-SPECIFIED: the PRD states no explicit acceptance criteria for this section. They must be written before this requirement leaves `draft`._

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
