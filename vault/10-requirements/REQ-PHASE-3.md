---
id: REQ-PHASE-3
title: Derivatives
type: phase
prd_ref: "Phase 3 — Derivatives"
prd_lines: "6759-6775"
phase: 3
status: implemented
depends_on: ["REQ-PHASE-2"]
tags: []
covers: [REQ-WP-013, REQ-SCORE-001, REQ-BIAS-005, REQ-EXP-006, REQ-WP-026, REQ-WP-030, REQ-WP-031]
not_delivered: []
blocked: []
deferred: []
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

Closed 2026-09-10 by [[REQ-WP-031]], the last of the seven deliverables. The
phase reads as three concerns rather than seven items:

- **the features exist** — [[REQ-WP-013]] carries funding, OI, basis and the
  liquidation feed; [[REQ-WP-031]] adds long/short positioning;
- **they cannot lie about their age** — [[REQ-WP-026]] is the phase's second
  acceptance line ("stale REST polling cannot silently reuse old value") made
  mechanical, and [[REQ-WP-031]] applies the same rule to the newest published
  reading rather than the newest state, which is the same failure one level in;
- **they are visible and they score** — [[REQ-WP-030]] is the derivatives panel,
  [[REQ-SCORE-001]] the score integration.

Both acceptance lines hold. Point-in-time safety is asserted per feature rather
than claimed once: every reading is a function of a state list and the instant
asked about, and each has a test built to fail if it reads past that instant.

What the phase does **not** do, and never claimed to: nothing writes derivative
features into the feature table yet. The panes render "no readings" and the
readings return refusals over empty history. That is ingestion-path work, and it
is honest about being absent, which is the property this phase spent most of its
tests on.
