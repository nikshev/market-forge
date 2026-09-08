---
id: REQ-NRT-C
title: confirmation legality
type: constraint
hard_gated: true
prd_ref: "Test C — confirmation legality"
prd_lines: "2232-2239"
phase: null
status: specified
depends_on: []
tags: []
---

## Requirement

```text
known_at >= extremum_time
```

and the confirmation logic must not read events with `available_at > known_at`.

## Acceptance

- `known_at >= extremum_time` holds for every confirmed extremum;
- confirmation logic never reads events with `available_at > known_at`.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Outcomes:** [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
