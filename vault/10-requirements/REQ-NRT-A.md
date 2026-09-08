---
id: REQ-NRT-A
title: future-bar invariance
type: constraint
hard_gated: true
prd_ref: "Test A — future-bar invariance"
prd_lines: "2220-2227"
phase: null
status: specified
depends_on: []
tags: []
---

## Requirement

Compute live outputs up to `t`.

Append arbitrary bars after `t`.

Assert all finalized outputs with `available_at <= t` remain byte-equivalent.

## Acceptance

- given live outputs computed up to `t`, appending arbitrary bars after `t` does not change any finalized output with `available_at <= t` (byte-equivalent before and after).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Outcomes:** [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
