---
id: REQ-EXP-008
title: GMDH vs baselines
type: experiment
prd_ref: "EXP-008 GMDH vs baselines"
prd_lines: "5127-5145"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

Same point-in-time feature matrix.

Models:

- logistic;
- elastic net;
- gradient boosting;
- GMDH.

Evaluate:

- Brier;
- calibration;
- PR-AUC;
- expectancy by probability bucket;
- feature stability across walk-forward folds.

## Acceptance

_The PRD states no explicit acceptance criteria for this section. They must be written before this requirement leaves `draft`._

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
