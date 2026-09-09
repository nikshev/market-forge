---
id: OUT-2026-09-09-spec-bars-table
step: spec
records: [REQ-TBL-001]
commit: null
---

## What was done

`specs/054-bars-table/spec.md`: three user stories, 9 functional requirements,
10 success criteria.

## What was decided

- **The event-time column is the bar's close** (FR-004). It reads like a column
  choice and is a look-ahead rule.
- **Money round-trips exactly** (FR-001), which needed a new column type on the
  plane.
- **`is_final` is deliberately not a column** (FR-003): it would be `true` on
  every row, and the refusal on the way in carries the same meaning without
  leaving a door open.

## What is still open

- Nothing from this step.
