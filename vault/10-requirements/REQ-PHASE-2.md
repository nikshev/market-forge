---
id: REQ-PHASE-2
title: CEX microstructure
type: phase
prd_ref: "Phase 2 — CEX microstructure"
prd_lines: "6738-6758"
phase: 2
status: planned
depends_on: ["REQ-PHASE-1A"]
tags: []
covers: [REQ-WP-004, REQ-WP-011, REQ-WP-012, REQ-NRT-E, REQ-EXP-004, REQ-EXP-005]
not_delivered:
  - "UI panes for the book features: the web app has no order-book or order-flow pane"
---

## Requirement

Deliverables:

- L2 order book reconstruction;
- book health;
- queue imbalance;
- multi-depth imbalance;
- OFI;
- CVD;
- wall persistence/cancellation;
- absorption feature;
- volume profile;
- UI panes.

Acceptance:

- forced sequence gap disables book features;
- replay parity on captured stream;
- OFI features available in signal snapshot.

## Acceptance

- forced sequence gap disables book features;
- replay parity on captured stream;
- OFI features available in signal snapshot.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-004]]
- [[REQ-WP-011]]
- [[REQ-WP-012]]
- [[REQ-NRT-E]]
- [[REQ-EXP-004]]
- [[REQ-EXP-005]]

**Not delivered:**

- UI panes for the book features: the web app has no order-book or order-flow pane

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_2_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
