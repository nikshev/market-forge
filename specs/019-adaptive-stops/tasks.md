---
description: "Task list for REQ-WP-020 and REQ-BIAS-009"
---

# Tasks: Adaptive stop management

- [x] T001 Write failing `test_policy.py`: the monotonic rule on both sides; a future anchor never used; every proposal carries a reason; sub-threshold, cooldown, freeze and minimum-distance holds; the noise buffer; a stop beyond the market refused (SC-001 to SC-006).
- [x] T002 Implement `models.py` — §44A.3's fields, frozen, with the initial-risk contract validated at construction (FR-010, FR-011).
- [x] T003 Implement `policy.py` — §44A.16's pipeline (FR-001 to FR-009, FR-018).
- [x] T004 Write failing `test_replay.py`: realized R net of fees and slippage; the executable exit; the premature-stop metric; the naive baselines; determinism (SC-007 to SC-009).
- [x] T005 Implement `replay.py` with §44A.23's cost model and §44A.29's metric (FR-012 to FR-016).
- [x] T006 Mutation-check six guards, verifying every restore.
- [x] T007 Assert no module consults a clock (FR-017).
- [x] T008 Markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-009, FR-018 | T003 |
| FR-010, FR-011 | T002 |
| FR-012 to FR-016 | T005 |
| FR-017 | T007 |
| SC-001 to SC-006 | T001 |
| SC-007 to SC-009 | T004 |
| SC-010 | T007 |

## Notes

Two mutations survived the first sweep and both found real gaps: removing the
post-buffer monotonic check was masked by the initial-risk guard catching the
same proposals, and removing the `reasons` minimum length changed no behaviour
because every call site passes one. The tests added for them are the ones that
separate a guard from its neighbour.
