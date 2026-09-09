---
id: REQ-PHASE-0
title: Repository + correctness skeleton
type: phase
prd_ref: "Phase 0 — Repository + correctness skeleton"
prd_lines: "6675-6694"
phase: 0
status: planned
depends_on: []
tags: []
covers: [REQ-WP-001, REQ-WP-002, REQ-INFRA-001, REQ-INFRA-002]
not_delivered:
  - "event bus abstraction: components are wired directly, with no bus between them"
---

## Requirement

Deliverables:

- repo layout;
- domain models;
- config loader;
- Docker Compose;
- Postgres/ClickHouse connectivity;
- virtual clock;
- event bus abstraction;
- CI;
- golden test framework.

Acceptance:

- `make test` green;
- services boot locally;
- canonical event serialization roundtrip.

## Acceptance

- `make test` green;
- services boot locally;
- canonical event serialization roundtrip.

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-001]]
- [[REQ-WP-002]]
- [[REQ-INFRA-001]]
- [[REQ-INFRA-002]]

**Not delivered:**

- event bus abstraction: components are wired directly, with no bus between them

Two other deliverables are **not** on that list, and both were on it in the first
version of this note.

The **virtual clock** is delivered, by a stronger construction than the PRD asks
for: no module in `src/` reads a wall clock at all. Time is event time carried on
the data, a `Clock` protocol with a driven fake exists where a lifetime has to be
measured, and ten packages carry import-ban tests asserting they cannot consult a
clock — `tests/unit/backtest/test_virtual_clock.py` among them. A virtual clock
exists to make replay deterministic; here that property holds because there is
nothing to virtualize.

"Postgres/ClickHouse connectivity" is also not on it. [[ADR-002]] dropped
ClickHouse and adopted the PRD's own target storage profile from the start —
PostgreSQL for transactional metadata and S3-compatible object storage as the
canonical data plane — and both are provisioned. The PRD's wording is provenance
for a decision already taken, not an outstanding deliverable, and the Notes
section below has said so since the phase note was written.

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_0_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

The requirement body above quotes PRD Phase 0 verbatim and lists
"Postgres/ClickHouse connectivity". ClickHouse was subsequently dropped in favour of
the PRD's own target storage profile — see [[ADR-002]]. The PRD text stands as
provenance; the ADR is what the implementation follows.

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
