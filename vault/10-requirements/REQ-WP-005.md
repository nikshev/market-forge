---
id: REQ-WP-005
title: Bar aggregation
type: work-package
prd_ref: "WP-005 Bar aggregation"
prd_lines: "6968-6974"
phase: null
status: specified
depends_on: [REQ-WP-002, REQ-WP-003]
tags: []
---

## Requirement

- event-time windows;
- late-event policy;
- finalized bar callback;
- trade-side aggregates.

## Acceptance

- bars aggregate on event-time windows;
- a late-event policy is enforced;
- a finalized-bar callback fires on close;
- trade-side aggregates are produced per bar.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-006-bar-aggregation]]
- **Outcomes:** [[OUT-2026-09-08-spec-bar-aggregation]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
