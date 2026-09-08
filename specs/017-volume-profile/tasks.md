---
description: "Task list for REQ-WP-012"
---

# Tasks: Volume profile

## Phase 1: Binning and the value area (US1, US2)

- [ ] T001 Write failing `test_profile.py`: bins hand-summed from trades; buy/sell from the aggressor side and unknown counted in neither; boundary trades resolved consistently; POC with its tie-break recorded; the value area contiguous, containing the POC, holding the configured share; the target-not-met flag; an empty window refuses (SC-001 to SC-004, SC-007). Confirm RED.
- [ ] T002 Implement `profile.py` (FR-001 to FR-007).

## Phase 2: Nodes (US3)

- [ ] T003 Write failing `test_nodes.py`: a shelf is a high-volume node; a gap is a low-volume node; a uniform profile has none; channel boundaries are matched to the nodes they fall inside (SC-005). Confirm RED.
- [ ] T004 Implement `nodes.py` (FR-008, FR-009, FR-011).

## Phase 3: Shape (US4)

- [ ] T005 Write failing `test_shape.py`: entropy lower for a concentrated profile; skew positive with more volume above the POC; distances in bps (SC-006). Confirm RED.
- [ ] T006 Implement `shape.py`, register its features, and extend `exposed_feature_names()` (FR-010, FR-013, SC-009).

## Phase 4: The chart plugin (US5)

- [ ] T007 Write failing `volumeProfile.test.ts`: bar lengths proportional to bin volume; the POC and value-area bounds marked; no profile draws nothing (SC-008). Confirm RED.
- [ ] T008 Implement `volumeProfile.ts` and draw it in `Chart.tsx` (FR-012).

## Phase 5: Close

- [ ] T009 Mutation-check five guards: infer sides from bar direction; let the value area be non-contiguous; drop the POC tie-break; return an empty profile instead of refusing; drop a registration. Verify every restore.
- [ ] T010 Assert no module consults a clock (FR-014).
- [ ] T011 Markers, statuses, and all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-007 | T002 |
| FR-008, FR-009, FR-011 | T004 |
| FR-010, FR-013 | T006 |
| FR-012 | T008 |
| FR-014 | T010 |
| SC-001 to SC-004, SC-007 | T001 |
| SC-005 | T003 |
| SC-006 | T005 |
| SC-008 | T007 |
| SC-009 | T006 |

## Notes

T009's second mutation is the one worth the effort. A value area assembled by
descending volume rather than by expansion still holds 70% and still has a VAH
and a VAL — it is simply a different region, with a hole in it, and nothing
about the numbers says so.
