---
id: REQ-PHASE-1A
title: Extremum baseline
type: phase
prd_ref: "Phase 1A — Extremum baseline"
prd_lines: "6720-6737"
phase: 1A
status: implemented
depends_on: ["REQ-PHASE-1"]
tags: []
covers: [REQ-WP-019, REQ-NRT-A, REQ-NRT-B, REQ-NRT-C, REQ-NRT-E, REQ-EXP-011, REQ-EXP-012, REQ-WP-028]
not_delivered: []
blocked: []
deferred: []
---

## Requirement

Deliverables:

- directional-change confirmed highs/lows;
- causal local-polynomial slope/curvature;
- extremum candidate lifecycle;
- immutable `extremum_time` vs `known_at` semantics;
- chart markers for candidate vs confirmed extrema;
- replay/non-repaint tests;
- no ML required.

Acceptance:

- no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;
- appending future bars does not mutate finalized candidates/confirmed extrema;
- confirmation lag and prominence are reported.

## Acceptance

- no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;
- appending future bars does not mutate finalized candidates/confirmed extrema;
- confirmation lag and prominence are reported.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-019]]
- [[REQ-NRT-A]]
- [[REQ-NRT-B]]
- [[REQ-NRT-C]]
- [[REQ-NRT-E]]
- [[REQ-EXP-011]]
- [[REQ-EXP-012]]

**Not delivered:**

- chart markers for candidate versus confirmed extrema: the web chart draws channels and volume profile, not extrema

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_1a_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]], [[OUT-2026-09-10-implement-extremum-markers]]
<!-- trace:end -->

## Notes

`not_delivered` is empty as of 2026-09-10 — the sixth phase to reach
`implemented`. The last entry to leave was "chart markers for candidate versus
confirmed extrema", closed by [[REQ-WP-028]].

That deliverable turned out to be four layers rather than a drawing change: the
detector's output reached no table, no repository and no endpoint. The phase's
own acceptance criterion — no confirmed extremum earlier than `known_at` in
`AS-SEEN-THEN` — is now enforced by the storage, because `known_at_ns` is the
table's event time.

**The tables are reachable and empty.** Nothing runs the detector into them yet.

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
