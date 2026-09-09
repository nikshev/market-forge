---
description: "Task list for REQ-EXP-013"
---

# Tasks: GMDH derivative extrema

- [x] T001 Extract `read_derivative_folds` from `run_derivative_experiment`, keeping the existing tests green.
- [x] T002 Export the readings and `wanted_turn_type` from `channelflow.turning`.
- [x] T003 Write failing tests for the shape: four arms, seven metrics, absent metrics on the classifier arms (SC-001, SC-002, SC-005).
- [x] T004 Implement `gmdh_extrema.py`: the four arms, the metrics, the economics (FR-001 to FR-012).
- [x] T005 Implement and test the verdict, both halves and both together (FR-013, SC-009 to SC-012).
- [x] T006 Export it from `channelflow.research` and add the trace marker.
- [x] T007 Mutation-check fourteen guards with the bounded runner, verifying every restore.
- [x] T008 Close the two the sweep found: the horizon IQR's denominator and the call with no true turn.
- [x] T009 Record [[ADR-051]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002 | T003, T004 |
| FR-003 | T004, T008 |
| FR-004 | T003, T004 |
| FR-005, FR-006 | T004, T008 |
| FR-007 to FR-009 | T004 |
| FR-010 to FR-012 | T004 |
| FR-013 | T005 |
| FR-014 | T004 |
| SC-001, SC-002, SC-005 | T003 |
| SC-003, SC-004 | T008 |
| SC-006, SC-007 | T004, T008 |
| SC-008 | T004 |
| SC-009 to SC-012 | T005 |
| SC-013 to SC-015 | T004 |

## Notes

T008's two survivors were both denominators no fixture could see. The horizon
IQR averaged over every scored row is exactly half the right answer on a fixture
where half the paths run straight, and no test named the number — the reference
is now the production stability function's own answer for the fixture's path,
not a figure written into the test. And no fixture contained a call whose true
path never turned, because every fixture's paths were a clean function of its
features; keying the paths to a period neither feature follows makes the
networks predict the average path, which turns, and 41 of 64 calls then land on
rows with nothing to be wrong about.
