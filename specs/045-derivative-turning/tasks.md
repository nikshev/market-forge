---
description: "Task list for REQ-EXP-012"
---

# Tasks: Causal derivative turning points

- [x] T001 Fix the `Transform` Protocol so a frozen transform can satisfy it.
- [x] T002 Write failing tests for the shape: four candidates, four horizons, a centred candidate refused (SC-001 to SC-003, SC-006).
- [x] T003 Implement `derivative_turning.py`: the labeller, the four estimators, the comparison (FR-001 to FR-011).
- [x] T004 Export it from `channelflow.research` and add the trace marker.
- [x] T005 Mutation-check nine guards with the bounded runner, verifying every restore.
- [x] T006 Close the three the sweep found: the right edge, the horizon, and the note's first half.
- [x] T007 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T002, T003 |
| FR-002, FR-003 | T001, T002, T003 |
| FR-004, FR-005 | T003, T006 |
| FR-006 | T002, T006 |
| FR-007 | T003, T006 |
| FR-008 to FR-011 | T003 |
| SC-001 to SC-003, SC-006 | T002 |
| SC-004, SC-005 | T003, T006 |
| SC-007, SC-009 | T006 |
| SC-008, SC-010 to SC-012 | T003 |

## Notes

T006's two hard survivors both came from fixtures that could not see the
difference. The rising-then-falling fixture reports the same slope at the peak
whether the fit is read at its centre or its right edge, so the mutation that
moved the read point changed nothing measurable — three bars past the peak the
two differ in sign (-0.46 against +0.63), and that is where the test now looks.
And on a swing series three of the four methods score 1.0 at every horizon, so
the horizon could be dropped from the arithmetic without any number changing; a
triangle with one labelled turn and a call eight bars early separates them.
