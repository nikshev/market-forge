---
description: "Task list for REQ-EXP-008"
---

# Tasks: GMDH against the baselines

- [x] T001 Implement `regularized.py` with required penalty and L1 ratio, and a soft-thresholding step (FR-002, FR-003).
- [x] T002 Implement `boosting.py` with depth-limited trees, exhaustive splits and a minimum leaf size (FR-004 to FR-007).
- [x] T003 Wire both into the comparison report and update ADR-029's not-run list (FR-001, FR-013).
- [x] T004 Implement `metrics.py`: calibration, PR-AUC, bucket expectancy, feature stability (FR-008 to FR-012).
- [x] T005 Write the tests, including the interaction target that separates a real tree from a stump booster (SC-002).
- [x] T006 Mutation-check fourteen guards with the bounded runner, verifying every restore.
- [x] T007 Close the two the sweep found: partial feature overlap, and the leaf-size guard.
- [x] T008 [[ADR-050]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-013 | T003 |
| FR-002, FR-003 | T001 |
| FR-004 to FR-007 | T002, T007 |
| FR-008 to FR-012 | T004, T007 |
| SC-001 | T003 |
| SC-002 to SC-005 | T005 |
| SC-006 to SC-010 | T005, T007 |
| SC-011 | T007 |

## Notes

T002's first version was a stump booster with an unused `max_depth` field. It
scored 0.238 against logistic regression's 0.237 on an interaction target — the
poor tree ADR-029 warned about, and a field that did nothing. Real depth-two
trees score 0.025 on the same target.
