---
description: "Task list for REQ-US-007"
---

# Tasks: Nothing trains on an unchecked dataset

- [x] T001 Write failing `test_training_gate.py`: a clean dataset certifies, a leaked label refuses by rule name, an empty dataset refuses (SC-001, SC-002, SC-004).
- [x] T002 Write the no-back-door test: a certificate built around an unclean report is refused (SC-005).
- [x] T003 Implement `certified.py` — `CertifiedDataset` and `certify` (FR-001 to FR-005, FR-008, FR-009).
- [x] T004 Change `run_direct_baseline`, `run_derivative_experiment` and `run_ablation` to take a certificate and read their folds from it (FR-006, FR-007).
- [x] T005 Write the signature test over all three entry points (SC-007).
- [x] T006 Update every existing caller, and add a `certified` fixture so a test's dataset is checked the way a caller's is.
- [x] T007 Write the contaminated-fold test: clean rows, a fold that trains on its own validation window (SC-003).
- [x] T008 Mutation-check six guards with the bounded runner, verifying every restore.
- [x] T009 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-005, FR-008, FR-009 | T003 |
| FR-006 | T004, T005 |
| FR-007 | T004 |
| SC-001, SC-002, SC-004 | T001 |
| SC-003 | T007 |
| SC-005 | T002 |
| SC-006, SC-007 | T005 |
| SC-008 | T001 |

## Notes

T007 came out of the sweep: dropping the fold report from the certificate's own
check changed nothing, because every fixture with clean rows also had clean
folds. The two checks answer different questions, and a fold builder gets the
second one wrong in a way no labeller would.
