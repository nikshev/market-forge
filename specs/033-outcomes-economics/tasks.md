---
description: "Task list for REQ-BT-001"
---

# Tasks: Signal outcomes, fill models and economic metrics

- [x] T001 Write failing `test_outcomes.py` for the four outcomes, including a bar containing both levels (SC-001, SC-002).
- [x] T002 Write failing tests for the edges: a touch at exactly the level, a short resolved by its own direction, a horizon past the data (SC-003, SC-004).
- [x] T003 Implement `outcomes.py` (FR-001 to FR-007).
- [x] T004 Write failing fill tests: next open, refusal without one, slippage both directions, phase-2 named (SC-005, SC-006).
- [x] T005 Implement `fills.py` (FR-008 to FR-010).
- [x] T006 Write failing `test_economics.py`: every §25.5 metric, refusal without costs, metrics after costs, ambiguous excluded and counted (SC-007 to SC-011).
- [x] T007 Implement `economics.py` (FR-011 to FR-016).
- [x] T008 Assert the package consults no clock (SC-012, FR-017).
- [x] T009 Mutation-check fifteen guards with the bounded runner, verifying every restore.
- [x] T010 Remove the redundant ambiguity guard the sweep exposed, and re-sweep against the loop's `break`.
- [x] T011 [[ADR-048]] superseding [[ADR-009]]'s restriction; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-007 | T003 |
| FR-008 to FR-010 | T005 |
| FR-011 to FR-016 | T007 |
| FR-017 | T008 |
| SC-001 to SC-004 | T001, T002 |
| SC-005, SC-006 | T004 |
| SC-007 to SC-011 | T006 |
| SC-012 | T008 |

## Notes

T010 is the interesting one. The mutation "an ambiguous bar keeps a touch time"
survived because the branch breaks before either time can be set — so the guard
was unreachable, and while it stood, deleting that `break` changed no test.
