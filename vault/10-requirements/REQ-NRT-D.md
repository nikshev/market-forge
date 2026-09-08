---
id: REQ-NRT-D
title: centered filter prohibition
type: constraint
hard_gated: true
prd_ref: "Test D — centered filter prohibition"
prd_lines: "2240-2243"
phase: null
status: specified
depends_on: []
tags: []
---

## Requirement

Production feature path fails validation if a transform declares symmetric/centered future dependence.

## Acceptance

- the production feature path fails validation if any transform declares symmetric/centered future dependence.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Outcomes:** [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
