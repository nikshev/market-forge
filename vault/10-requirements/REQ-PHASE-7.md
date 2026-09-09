---
id: REQ-PHASE-7
title: ML/GMDH
type: phase
prd_ref: "Phase 7 — ML/GMDH"
prd_lines: "6845-6870"
phase: 7
status: planned
depends_on: ["REQ-PHASE-6"]
tags: []
covers: [REQ-WP-017, REQ-WP-018, REQ-WP-019, REQ-SCORE-001, REQ-EXP-008, REQ-EXP-013, REQ-NRT-F, REQ-US-004]
not_delivered:
  - "model registry: models are constructed by callers and are not registered or versioned"
  - "P(max)/P(min)/P(no-turn) calibration by horizon: calibration exists, but not sliced by horizon"
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

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/unit/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-017]]
- [[REQ-WP-018]]
- [[REQ-WP-019]]
- [[REQ-SCORE-001]]
- [[REQ-EXP-008]]
- [[REQ-EXP-013]]
- [[REQ-NRT-F]]
- [[REQ-US-004]]

**Not delivered:**

- model registry: models are constructed by callers and are not registered or versioned
- P(max)/P(min)/P(no-turn) calibration by horizon: calibration exists, but not sliced by horizon

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_7_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
