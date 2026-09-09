---
description: "Task list for REQ-EXP-006"
---

# Tasks: Derivatives context

- [x] T001 Write failing tests for the shape: four variables, declared edges, counts summing to the sample (SC-001, SC-002).
- [x] T002 Write the failing unavailable-variable test (SC-005).
- [x] T003 Implement `derivatives_context.py` (FR-001 to FR-007, FR-009, FR-010).
- [x] T004 Write the failing label tests, and assert the flag has no default (SC-006).
- [x] T005 Write the cost tests: same model everywhere, and raising them lowers every bucket (SC-008).
- [x] T006 Write the thin-bucket and ambiguity tests (SC-003, SC-007).
- [x] T007 Mutation-check ten guards with the bounded runner, verifying every restore.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-004 | T001, T006 |
| FR-005 | T002 |
| FR-006 | T005 |
| FR-007 | T006 |
| FR-008 | T004 |
| FR-009, FR-010 | T003 |
| SC-001, SC-002 | T001 |
| SC-003, SC-007 | T006 |
| SC-004 | T001 |
| SC-005 | T002 |
| SC-006 | T004 |
| SC-008 | T005 |
| SC-009, SC-010 | T003 |

## Notes

T006's thin-bucket test needed its own edges. With the default ones the three
extra setups joined the twenty already in that band, and the bucket under test
was not thin at all — a fixture agreeing with the assertion for the wrong
reason.
