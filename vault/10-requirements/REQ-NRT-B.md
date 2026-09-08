---
id: REQ-NRT-B
title: candidate chronology
type: constraint
hard_gated: true
prd_ref: "Test B — candidate chronology"
prd_lines: "2228-2231"
phase: null
status: specified
depends_on: []
tags: []
---

## Requirement

A candidate may be invalidated later, but its original snapshot cannot change.

## Acceptance

- a candidate's original snapshot never changes, even when the candidate is later invalidated.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Outcomes:** [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
