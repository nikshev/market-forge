---
id: REQ-PHASE-3
title: Derivatives
type: phase
prd_ref: "Phase 3 — Derivatives"
prd_lines: "6759-6775"
phase: 3
status: planned
depends_on: ["REQ-PHASE-2"]
tags: []
covers: [REQ-WP-013, REQ-SCORE-001, REQ-BIAS-005, REQ-EXP-006]
not_delivered:
  - "derivatives feature panel: the web app has no derivatives pane"
  - "optional long/short stats: not ingested"
---

## Requirement

Deliverables:

- funding;
- OI;
- basis;
- liquidation feed;
- optional long/short stats;
- derivatives feature panel;
- score integration.

Acceptance:

- all derivative features point-in-time safe;
- stale REST polling cannot silently reuse old value.

## Acceptance

- all derivative features point-in-time safe;
- stale REST polling cannot silently reuse old value.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-013]]
- [[REQ-SCORE-001]]
- [[REQ-BIAS-005]]
- [[REQ-EXP-006]]

**Not delivered:**

- derivatives feature panel: the web app has no derivatives pane
- optional long/short stats: not ingested

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_3_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
