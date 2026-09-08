---
id: REQ-WP-004
title: Order book service
type: work-package
prd_ref: "WP-004 Order book service"
prd_lines: "6959-6967"
phase: null
status: planned
depends_on: ["REQ-WP-003"]
tags: []
---

## Requirement

- buffer + snapshot bootstrap;
- exact sequence validation;
- rebuild on gap;
- top-N access;
- depth-at-bps query;
- health state.

## Acceptance

- book bootstraps from a buffered snapshot;
- sequence numbers are validated exactly;
- book rebuilds on a detected sequence gap;
- top-N levels are accessible;
- depth-at-bps can be queried;
- book health state is reported.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-010-order-book-service]]
- **Code:**
    - `src/channelflow/book/book.py`
- **Outcomes:** [[OUT-2026-09-08-plan-order-book-service]], [[OUT-2026-09-08-spec-order-book-service]], [[OUT-2026-09-08-tasks-order-book-service]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
