---
description: "Task list for REQ-EXP-010"
---

# Tasks: Cross-venue lead/lag value

- [x] T001 Write failing tests for the shape: a predictive divergence reaching `EDGE`, a wrong-way one not (SC-001).
- [x] T002 Write failing latency tests: the edge falls with delay, no default, negatives refused (SC-005, SC-006).
- [x] T003 Implement `lead_lag_value.py` (FR-001 to FR-012).
- [x] T004 Write the split tests: in-sample selection, one-sided signals refusing to validate (SC-002, SC-003).
- [x] T005 Write the import-ban test over the signal path (SC-010).
- [x] T006 Mutation-check ten guards with the bounded runner, verifying every restore.
- [x] T007 Close the five the sweep found: in-sample counting, the threshold tie, direction, all-ambiguous outcomes, and the costs refusal firing first.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-004 | T004, T007 |
| FR-005, FR-006 | T002 |
| FR-007 | T007 |
| FR-008, FR-009 | T007 |
| FR-010 | T001 |
| FR-011 | T005 |
| FR-012 | T003 |
| SC-001 | T001 |
| SC-002 to SC-004 | T004, T007 |
| SC-005 to SC-007 | T002, T007 |
| SC-008, SC-009 | T007 |
| SC-010, SC-011 | T005, T003 |

## Notes

The first fixture put its price move one bar after the signal, which is the bar
the fill happens on — so the trade entered at the post-move price and caught
nothing. The move now lands two bars later. A fixture that cannot reward a
correct prediction cannot distinguish a working study from a broken one.
