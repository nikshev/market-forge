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
  - "virtual clock: no clock abstraction exists; time comes from the event stream and from the connectors' own session"
  - "event bus abstraction: components are wired directly, with no bus between them"
  - "ClickHouse connectivity: the stack provisions PostgreSQL and MinIO only"
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
`tests/unit/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

- [[REQ-WP-001]]
- [[REQ-WP-002]]
- [[REQ-INFRA-001]]
- [[REQ-INFRA-002]]

**Not delivered:**

- virtual clock: no clock abstraction exists; time comes from the event stream and from the connectors' own session
- event bus abstraction: components are wired directly, with no bus between them
- ClickHouse connectivity: the stack provisions PostgreSQL and MinIO only

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
