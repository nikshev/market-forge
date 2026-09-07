---
id: REQ-PHASE-7
title: ML/GMDH
type: phase
prd_ref: "Phase 7 — ML/GMDH"
prd_lines: "6845-6870"
phase: 7
status: draft
depends_on: []
tags: []
---

## Requirement

Deliverables:

- candidate labeler;
- logistic baseline;
- boosted tree baseline;
- GMDH implementation/wrapper;
- calibration;
- probability ranker;
- explainability;
- model registry;
- turning-point direct classifier/regressor;
- GMDH bounded forward-path option;
- derivative root extractor;
- derivative-root stability report;
- P(max)/P(min)/P(no-turn) calibration by horizon.

Acceptance:

- GMDH cannot be promoted unless it beats baseline OOS on predeclared metrics;
- no feature leakage tests failing;
- calibration report included.

## Acceptance

- GMDH cannot be promoted unless it beats baseline OOS on predeclared metrics;
- no feature leakage tests failing;
- calibration report included.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
