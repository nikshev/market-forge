---
description: "Task list for REQ-US-001 and REQ-US-004"
---

# Tasks: A ranked market list and a signal's contribution factors

- [x] T001 Write failing `test_scored_markets.py` for the order: rank score descending, an illiquid high score below a liquid lower one, the same order twice, a filtered list still ordered (SC-001 to SC-003, SC-005).
- [x] T002 Write failing tests for the unscored market: sorts last, reports nulls, and the tail is ordered by name (SC-004).
- [x] T003 Add `ScoredSetup`, `add_setup_score` and `setup_score` to the repository and its protocol.
- [x] T004 Implement `ranking.py` — §43's order, unscored last (FR-001 to FR-003, FR-005).
- [x] T005 Extend `MarketOut` with setup score, rank score and confidence, nullable (FR-004).
- [x] T006 Write failing tests for the explanation: all five §22.4 items, all six groups accounted for, a missing family never negative, an unscored signal still returning (SC-006, SC-007).
- [x] T007 Add `FactorOut` and `ExplanationOut`, and attach the explanation in the signal detail (FR-006 to FR-009).
- [x] T008 Write failing `Explanation.test.tsx`, then the panel: six groups always, absence stated, a zero score distinguishable from absence (SC-008, FR-011).
- [x] T009 Mutation-check the surface with the bounded runner, verifying every restore.
- [x] T010 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003, FR-005 | T004 |
| FR-004 | T005 |
| FR-006 to FR-009 | T007 |
| FR-010 | T004 (the API ranks; it computes no score) |
| FR-011 | T008 |
| SC-001 to SC-003, SC-005 | T001 |
| SC-004 | T002 |
| SC-006, SC-007 | T006 |
| SC-008 | T008 |

## Notes

T002's tail test was written after the mutation sweep found that removing the
name tie-break changed nothing: the fixture held one unscored market, so the tie
it breaks never occurred.
