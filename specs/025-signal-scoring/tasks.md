---
description: "Task list for REQ-SCORE-001"
---

# Tasks: Deterministic signal score

- [x] T001 Write failing `test_score.py` around PRD §22.2's worked example: 81 raw, 0.96, 77.8 final; the six caps; an over-cap and a negative contribution refused; a duplicate group refused (SC-001, SC-002, SC-005).
- [x] T002 Implement `groups.py` — §22.1's groups, caps and the contribution's own range check (FR-001, FR-002).
- [x] T003 Write failing tests for the missing-family rule: distinguishable from a family scoring zero, confidence lowered by that family's cap, nothing present refused (SC-003, SC-004).
- [x] T004 Implement `score.py` (FR-003 to FR-008).
- [x] T005 Write failing `test_explain.py`: all five of §22.4's items, every group accounted for, factors ranked by share of cap, a missing family never a negative factor, no explanation without a score (SC-006, SC-007).
- [x] T006 Implement `explain.py` (FR-009 to FR-011).
- [x] T007 Write failing `test_ranker.py`: §43's product, an out-of-range factor refused, ranking total and stable, §22.3's threshold default and most-specific resolution (SC-008 to SC-010).
- [x] T008 Implement `ranker.py` (FR-012 to FR-014).
- [x] T009 Assert the package consults no clock (FR-015, SC-011).
- [x] T010 Mutation-check fifteen guards with the bounded runner, verifying every restore.
- [x] T011 [[ADR-044]]; markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002 | T002 |
| FR-003 to FR-008 | T004 |
| FR-009 to FR-011 | T006 |
| FR-012 to FR-014 | T008 |
| FR-015 | T009 |
| SC-001, SC-002, SC-005 | T001 |
| SC-003, SC-004 | T003 |
| SC-006, SC-007 | T005 |
| SC-008 to SC-010 | T007 |
| SC-011 | T009 |

## Notes

T005's ordering test is the one that matters most in a panel a person reads:
26 of 30 and 9 of 10 are both strong, but the second is stronger, and a list
ordered by raw contribution would lead with the channel group on every setup
simply because its cap is the largest.
