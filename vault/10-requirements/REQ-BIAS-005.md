---
id: REQ-BIAS-005
title: No using current funding settlement before it becomes known.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5321-5321"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No using current funding settlement before it becomes known.

## Acceptance

No using current funding settlement before it becomes known.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-016-derivatives]]
- **Tests:**
    - `tests/unit/derivatives/test_funding.py::test_an_unsettled_rate_is_not_used_at_t`
    - `tests/unit/derivatives/test_funding.py::test_the_unsettled_rate_becomes_usable_once_its_interval_closes`
- **Outcomes:** [[OUT-2026-09-08-implement-derivatives]], [[OUT-2026-09-08-spec-derivatives]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
