---
description: "Task list for REQ-EXP-016"
---

# Tasks: Multi-scale extrema

- [x] T001 Write failing tests for the shape: three rules, both deltas, the rejected set (SC-001, SC-004, SC-008).
- [x] T002 Implement `HigherFrame`, `Candidate` and `available_frame` with the closing guard (FR-007 to FR-009).
- [x] T003 Implement the three predicates (FR-001 to FR-004).
- [x] T004 Implement the pricing and the two deltas (FR-005, FR-006, FR-010).
- [x] T005 Implement the reading and its floor (FR-011, FR-012).
- [x] T006 Export it from `channelflow.research` and add the trace marker.
- [x] T007 Mutation-check sixteen guards with the bounded runner, verifying every restore.
- [x] T008 Close the three the sweep found: the multi-scale conjunction, the zone's edges, and the floor's role.
- [x] T009 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T001, T003 |
| FR-002, FR-003 | T008 |
| FR-004 | T003 |
| FR-005, FR-006 | T004 |
| FR-007 to FR-009 | T002 |
| FR-010 | T004 |
| FR-011 | T005, T008 |
| FR-012, FR-013 | T005 |
| SC-001, SC-004, SC-008 | T001 |
| SC-002, SC-003 | T008 |
| SC-005 to SC-007 | T005 |
| SC-009 to SC-011 | T002 |
| SC-012 | T004 |
| SC-013 | T008 |
| SC-014, SC-015 | T002, T004 |

## Notes

T008 also changed the reading rule. The floor had been applied to both the
per-trade delta and the total delta, which is one number meaning two things: a
per-trade R and a sum of R over sixty trades are not comparable to the same
constant. The floor now guards the per-trade number, which is the one a filter
inflates by construction, and the total is simply asked whether it went up.

The other two survivors were fixture blindness of the ordinary kind. Every
candidate in the main fixture sits well inside the zone, so an exclusive upper
bound changed nothing; and no test read the multi-scale rule's composition, so
swapping its conjunction for a disjunction produced a rule that was merely
looser and still scored.
