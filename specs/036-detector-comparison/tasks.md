---
description: "Task list for REQ-EXP-003"
---

# Tasks: Rejection detector comparison

- [x] T001 Implement `WickOnly` and `TwoBarConfirmation` at REQ-WP-007's plugin point, with tests over hand-shaped bars (SC-007, SC-008).
- [x] T002 Write failing tests for the report's shape: four entries, the unavailable one named and unranked, a silent detector reporting its reason (SC-001, SC-002).
- [x] T003 Implement `detector_comparison.py` (FR-001 to FR-004, FR-010 to FR-012).
- [x] T004 Write the no-second-engine test over the module's source (SC-009).
- [x] T005 Mutation-check thirteen guards with the bounded runner, verifying every restore.
- [x] T006 Split `detector_metrics` from the run so the taken-back share can be tested, and add the four tests the sweep found missing (SC-004 to SC-006).
- [x] T007 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-004 | T002, T003 |
| FR-005, FR-006 | T006 |
| FR-007 | T006 |
| FR-008, FR-009 | T001 |
| FR-010 to FR-012 | T003 |
| SC-001 to SC-003 | T002 |
| SC-004 to SC-006 | T006 |
| SC-007, SC-008 | T001 |
| SC-009 | T004 |
| SC-010, SC-011 | T003 |

## Notes

T006 is the interesting task. Four mutations survived the first sweep and three
were ordinary fixture gaps, but the fourth — the taken-back share — could not be
reached by any bar series tried. Rather than manufacture one, the measurement was
separated from the run so the metric is computed from lives a test can construct.
