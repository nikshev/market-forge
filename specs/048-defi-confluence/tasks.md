---
description: "Task list for REQ-EXP-015"
---

# Tasks: Derivatives/DeFi confluence at turning points

- [x] T001 Write failing tests for the shape: five families, twelve strict arms, the basis prefix (SC-001 to SC-003).
- [x] T002 Implement the family taxonomy, the arm generator and the strictness check (FR-001 to FR-003).
- [x] T003 Implement the fold fingerprint and the cross-report refusal (FR-004 to FR-006).
- [x] T004 Implement the two-direction reading and its floor (FR-007 to FR-010, FR-012).
- [x] T005 Implement the instrument check (FR-011).
- [x] T006 Export it from `channelflow.research` and add the trace marker.
- [x] T007 Mutation-check fifteen guards with the bounded runner, verifying every restore.
- [x] T008 Close the two the sweep found: the fingerprint's spans and the improvement floor.
- [x] T009 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003 | T001, T002 |
| FR-004, FR-006 | T003 |
| FR-005 | T003, T008 |
| FR-007 to FR-010 | T004 |
| FR-011 | T005 |
| FR-012 | T004, T008 |
| FR-013 | T002 |
| SC-001 to SC-003 | T001 |
| SC-004 | T003 |
| SC-005 | T008 |
| SC-006 to SC-009 | T004 |
| SC-010, SC-011 | T005, T004 |
| SC-012 | T008 |
| SC-013 | T002 |

## Notes

T008's two survivors were both fixtures that could not reach the guard. The
fingerprint's spans never mattered because the two datasets compared differed in
their fold *count* as well — a second pair, three folds each over different
rows, separates them.

And no fixture landed a difference in the band between zero and the floor, so a
rule of "any improvement counts" agreed with the floor everywhere. Running the
same data at a floor of 0.9 Brier separates them: at that floor nothing counts
as helping, including a family that genuinely improves the score by a quarter of
a point.

Shrinking the fixture from 160 rows and four folds to 60 and three cut the
module's runtime from 71 seconds to 15. Twelve arms times three folds times four
baselines apiece is the cost, and it is paid on every commit.
