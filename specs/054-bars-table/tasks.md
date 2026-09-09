---
description: "Task list for REQ-TBL-001"
---

# Tasks: The `bars` canonical table

- [x] T001 Add the `decimal` column type to the plane: canonical encoding, Arrow mapping, the writer's conversion, and `decimal_columns` for readers.
- [x] T002 Write the PRD §29.4 schema and the row mapping both ways (FR-001, FR-003, FR-004).
- [x] T003 Refuse an unfinalized bar (FR-002).
- [x] T004 Implement the reads: order, filters, as-of (FR-005).
- [x] T005 Implement the sink and its batching (FR-006, FR-007).
- [x] T006 Write the tests, including the builder-hook one (SC-001 to SC-010).
- [x] T007 Mutation-check twelve guards with the bounded runner, verifying every restore.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T001, T002, T006 |
| FR-002, FR-003 | T003, T006 |
| FR-004 | T002, T006 |
| FR-005 | T004, T006 |
| FR-006, FR-007 | T005, T006 |
| FR-008 | T006 |
| FR-009 | T006 (the existing isolation tests) |
| SC-001 to SC-010 | T006 |

## Notes

Eleven of the twelve mutations were caught. The twelfth was not behavioural, and
that is the third time today the distinction has mattered.

Removing the explicit `Decimal(...)` conversion in `from_row` changes nothing,
because `Bar` is a Pydantic model and its validator coerces the exact string form
to the same `Decimal`. The conversion is not redundant — it is what keeps
`from_row` correct if the model's field type ever changes, and a `float` field
would coerce the same string silently and lose the exactness. But it is not a
behavioural guard today, and reporting it as an uncaught gap would have
overstated what the suite misses.
