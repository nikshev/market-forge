---
description: "Task list for REQ-US-006"
---

# Tasks: An ablation across feature families

- [x] T001 Write failing `test_ablation.py`: all five arms in the report, every scored arm on the same folds, an unknown family refused (SC-001, SC-002, SC-008).
- [x] T002 Write failing tests for what is not run: no features for a family, a duplicate feature set naming the earlier arm, neither ranked, nothing runnable saying so (SC-003 to SC-006).
- [x] T003 Implement `ablation.py` — the arms, resolution, and the report (FR-001 to FR-009).
- [x] T004 Check the missing family before the duplicate test, so the reason names the cause.
- [x] T005 Extract `rank_arms` and test the tie-break on a constructed tie (FR-007, SC-007).
- [x] T006 Write the overlap test: a feature in two families is counted once and ordered stably (FR-001).
- [x] T007 Write the containment test: `all_combined` holds every other arm's families (FR-002).
- [x] T008 Assert the package consults no clock and no random source (FR-011, SC-009).
- [x] T009 Mutation-check eight guards with the bounded runner, verifying every restore.
- [x] T010 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T003, T006 |
| FR-002 | T007 |
| FR-003 | T001 |
| FR-004, FR-005, FR-006, FR-008 | T002, T004 |
| FR-007 | T005 |
| FR-009 | T003 |
| FR-010 | T001 |
| FR-011 | T008 |
| SC-001, SC-002, SC-008 | T001 |
| SC-003 to SC-006 | T002 |
| SC-007 | T005 |
| SC-009 | T008 |

## Notes

T005, T006 and T007 were all written after the sweep. Each closes a property
that held over the fixture but was never distinguished by it: an exact tie
between arms, a feature belonging to two families, and an `all_combined` that is
missing one.
