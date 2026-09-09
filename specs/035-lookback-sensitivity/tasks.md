---
description: "Task list for REQ-EXP-002"
---

# Tasks: Lookback sensitivity

- [x] T001 Write failing tests for the sweep's shape: six lookbacks, one split, a lookback the series cannot hold reported without stopping the rest (SC-001, SC-002).
- [x] T002 Write failing plateau tests on hand-built sweeps: widest run, jagged has none, wider tolerance never shrinks it, an absent value splits it, ties declared (SC-003 to SC-005, SC-008).
- [x] T003 Write failing recommendation tests: plateau not peak, no plateau means no recommendation, the plateau travels with it (SC-006, SC-007).
- [x] T004 Implement `lookback_sensitivity.py` (FR-001 to FR-012).
- [x] T005 Mutation-check nine guards with the bounded runner, verifying every restore.
- [x] T006 Fix the three tests the sweep found weak: the centre against the edge, the outer costs refusal, and the series-length branch.
- [x] T007 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003 | T001 |
| FR-004 to FR-006, FR-010 | T002 |
| FR-007 to FR-009 | T003 |
| FR-011, FR-012 | T001 |
| SC-001, SC-002 | T001 |
| SC-003 to SC-005, SC-008 | T002 |
| SC-006, SC-007 | T003 |
| SC-009, SC-010 | T001 |

## Notes

T006's third fix is the instructive one. The original test asserted that *some*
lookback was unreported — and on a 400-bar series they all were, but because
nothing traded, not because the series was too short. The branch it meant to
test was never reached. A 280-bar series reaches it for the 200-bar lookback
alone, and the test now asserts which reason it got.
