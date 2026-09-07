---
id: REQ-PHASE-0
title: Repository + correctness skeleton
type: phase
prd_ref: "Phase 0 — Repository + correctness skeleton"
prd_lines: "6675-6694"
phase: 0
status: draft
depends_on: []
tags: []
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

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

The requirement body above quotes PRD Phase 0 verbatim and lists
"Postgres/ClickHouse connectivity". ClickHouse was subsequently dropped in favour of
the PRD's own target storage profile — see [[ADR-002]]. The PRD text stands as
provenance; the ADR is what the implementation follows.

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
