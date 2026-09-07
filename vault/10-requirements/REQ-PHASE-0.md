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

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
