---
description: "Task list for REQ-US-005"
---

# Tasks: Backtesting one setup family at a time

- [x] T001 Write failing `test_families.py`: a family's run opens only its own candidates, both families run on one series, the report names its family (SC-001, SC-003).
- [x] T002 Write the interference test with a family whose thresholds match the default machine, so only the restriction differs (SC-002).
- [x] T003 Implement `families.py` — `SetupFamily`, PRD §31's `upper_rejection_short`, and `middle_continuation_short` (FR-001, FR-006, FR-008).
- [x] T004 Add `SignalMachine.opens`, defaulting to every pair (FR-002, FR-003, FR-005).
- [x] T005 Give the runner a family and the report its name; put the family's thresholds in the configuration (FR-004, FR-007).
- [x] T006 Write the no-strategy-logic test over `families.py` (SC-007, FR-010).
- [x] T007 Add the rising-channel fixture and the direction test — the middle zone opens longs there (SC-001).
- [x] T008 Write the distinct-zone test: a narrower zone opens fewer candidates (SC-004).
- [x] T009 Mutation-check nine guards with the bounded runner, verifying every restore.
- [x] T010 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-006, FR-008 | T003 |
| FR-002, FR-003, FR-005 | T004 |
| FR-004, FR-007 | T005 |
| FR-009 | T002 |
| FR-010 | T006 |
| SC-001 | T001, T007 |
| SC-002 | T002 |
| SC-003 | T001 |
| SC-004 | T008 |
| SC-005 | T003 |
| SC-006 | T001 |
| SC-007 | T006 |

## Notes

T007 and T008 were both written after the sweep, and both close the same kind of
hole: the falling fixture only ever opens shorts, so a restriction matching the
boundary alone looked identical; and `upper_rejection_short`'s zone equals the
engine's own default, so a family whose zone was dropped behaved identically.
