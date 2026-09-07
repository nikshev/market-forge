---
id: REQ-NRT-C
title: confirmation legality
type: constraint
prd_ref: "Test C — confirmation legality"
prd_lines: "2232-2239"
phase: null
status: draft
depends_on: []
tags: []
---

## Requirement

```text
known_at >= extremum_time
```

and the confirmation logic must not read events with `available_at > known_at`.

## Acceptance

_ACCEPTANCE-NOT-SPECIFIED: the PRD states no explicit acceptance criteria for this section. They must be written before this requirement leaves `draft`._

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
