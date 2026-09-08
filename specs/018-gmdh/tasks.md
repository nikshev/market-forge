---
description: "Task list for REQ-WP-018"
---

# Tasks: GMDH layer

## Phase 1: The abstraction and its baselines (US4 in part)

- [x] T001 Write failing tests for the split guard and the baselines: overlapping splits refused; the base rate predicts the training frequency; logistic regression is deterministic (SC-002, SC-008). Confirm RED.
- [x] T002 Implement `base.py` — the protocol, `BaseRate`, `LogisticRegression`, `require_disjoint` (FR-002, FR-012).

## Phase 2: The search (US1, US2)

- [x] T003 Write failing `test_gmdh.py`: selection scores on held-out rows; the layer and width budgets hold; a non-improving layer stops the search; the stop reason is reported; too few inputs, a one-row scoring split and a constant target are refused; interactions resolve to input names (SC-001, SC-003 to SC-005). Confirm RED.
- [x] T004 Implement `gmdh.py` (FR-001, FR-003 to FR-008).

## Phase 3: The report (US4)

- [x] T005 Write failing `test_report.py`: model and baselines on identical data; all six of PRD §23.6's baselines named with a status; a tie does not beat the base rate; a noise model is reported as no better; GMDH beats the linear baseline on an interaction target (SC-006, SC-007). Confirm RED.
- [x] T006 Implement `report.py` (FR-009 to FR-011).

## Phase 4: Close

- [x] T007 Mutation-check six guards: score on the fitting split; allow overlapping splits; grow regardless of improvement; count a tie as beating the base rate; omit unrun baselines; ignore the width budget. Verify every restore.
- [x] T008 Assert no module consults a clock (FR-013).
- [x] T009 Markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-002, FR-012 | T002 |
| FR-001, FR-003 to FR-008 | T004 |
| FR-009 to FR-011 | T006 |
| FR-013 | T008 |
| SC-001 to SC-005 | T003 |
| SC-006, SC-007 | T005 |
| SC-008 | T003 |

## Notes

T007's first mutation is the one that matters: scoring on the fitting split is
GMDH's defining failure, and it is silent. The search grows to its budget, the
model looks excellent, and every number downstream describes a memorised
sample. The test that catches it scores against a deliberately contradictory
target, so a node reading its own training rows cannot help but look good.
