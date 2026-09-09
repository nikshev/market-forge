---
description: "Task list for REQ-CHAN-001"
---

# Tasks: Channel baselines B, C and D

- [x] T001 Write failing `test_baselines.py` for the shared contract: each names itself, refuses a short window, ignores bars after the instant (SC-001, SC-002).
- [x] T002 Extract `window.py` from baseline A and have it delegate.
- [x] T003 Write the failing wick test and implement `huber.py` (SC-003, FR-004 to FR-006).
- [x] T004 Write failing tests for baseline C: asymmetry, crossing, minimum width, slope consistency (SC-004 to SC-007).
- [x] T005 Implement `quantile.py` (FR-007 to FR-011).
- [x] T006 Write failing tests for baseline D: no state changes when later bars arrive, no backward pass, uncertainty reported, band widens (SC-008 to SC-010).
- [x] T007 Implement `kalman.py` (FR-012 to FR-014).
- [x] T008 Assert no baseline consults a clock (SC-011, FR-015).
- [x] T009 Mutation-check fourteen guards with the bounded runner, verifying every restore.
- [x] T010 Replace the quantile descent with the exact enumeration after the sweep exposed its flat-series behaviour.
- [x] T011 Strengthen the four tests the sweep found weak: the robust band, the minimum width, the Kalman band's margin, and that the filter tracks its data.
- [x] T012 [[ADR-047]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003 | T001, T002 |
| FR-004 to FR-006 | T003 |
| FR-007 to FR-011 | T005 |
| FR-012 to FR-014 | T007 |
| FR-015 | T008 |
| SC-001, SC-002 | T001 |
| SC-003 | T003, T011 |
| SC-004 to SC-007 | T004 |
| SC-008 to SC-010 | T006, T011 |
| SC-011 | T008 |

## Notes

T010 came out of T009. The mutation "the minimum width is not enforced"
survived, and the reason was not the test: a flat series was coming back with a
2.5% channel of its own, so the floor never bound. The floor was fine; the
estimator was not.
