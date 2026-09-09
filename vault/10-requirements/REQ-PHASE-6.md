---
id: REQ-PHASE-6
title: Research-grade validation
type: phase
prd_ref: "Phase 6 — Research-grade validation"
prd_lines: "6833-6844"
phase: 6
status: planned
depends_on: ["REQ-PHASE-5"]
tags: []
covers: [REQ-WP-017, REQ-US-006, REQ-US-007, REQ-NRT-E, REQ-BIAS-001, REQ-BIAS-003, REQ-BIAS-010]
not_delivered:
  - "experiment registry: experiments are modules and notes, not registered artifacts"
  - "dataset hashes: no dataset, config, commit or model-artifact hash is computed or recorded"
---

## Requirement

Deliverables:

- point-in-time dataset builder;
- event replay;
- walk-forward runner;
- ablation reports;
- experiment registry;
- dataset hashes;
- reproducible reports.

## Acceptance

- every dataset row satisfies `source_max_event_time <= as_of_time`, and a join that would violate it is refused rather than corrected (§24.1);
- labels may use future data and features may not, checked by a test rather than asserted (§24.2);
- primary evaluation uses chronological walk-forward splits with purge/embargo where horizons overlap, and never a random train/test split (§24.3, §41 rule 1);
- an ablation report names every arm that could not be run, and why, rather than omitting it (§23.6);
- an experiment is identified by the four hashes PRD §0 item 13 names -- dataset, config, code commit, model artifact -- and a report that cannot name all four is refused;
- re-running an experiment from the same four hashes reproduces its numbers exactly;
- a live event segment replayed offline reproduces feature, channel and signal values (§35.5).

_Derived, not quoted: the PRD states no acceptance criteria for this phase. Each line names the section it comes from; the derivation is recorded in `docs/superpowers/specs/2026-09-09-phase-acceptance-design.md`._

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/unit/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-017]]
- [[REQ-US-006]]
- [[REQ-US-007]]
- [[REQ-NRT-E]]
- [[REQ-BIAS-001]]
- [[REQ-BIAS-003]]
- [[REQ-BIAS-010]]

**Not delivered:**

- experiment registry: experiments are modules and notes, not registered artifacts
- dataset hashes: no dataset, config, commit or model-artifact hash is computed or recorded

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_6_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
