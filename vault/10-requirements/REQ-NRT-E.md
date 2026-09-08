---
id: REQ-NRT-E
title: replay parity
type: constraint
hard_gated: true
prd_ref: "Test E — replay parity"
prd_lines: "2244-2247"
phase: null
status: specified
depends_on: []
tags: []
---

## Requirement

Live recorded outputs and deterministic replay outputs must match for the same event stream/config/model artifact.

## Acceptance

- live recorded outputs and deterministic replay outputs match for the same event stream, config, and model artifact.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Outcomes:** [[OUT-2026-09-08-spec-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
