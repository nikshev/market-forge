---
description: "Task list for REQ-EXP-017"
---

# Tasks: Adaptive stop-management policy comparison

- [x] T001 Record the walk on `StopPolicyOutcome` and in both replay loops; pass `data_quality_ok` through ([[ADR-052]]).
- [x] T002 Test the replay's new output: the excursion both ways round, the holding time, the distances, the freeze.
- [x] T003 Write failing tests for the shape: seven policies, twelve metrics, seven ablations (SC-001, SC-003, SC-008).
- [x] T004 Implement `Capabilities`, `PathPoint` and `visible_path` (FR-011, FR-012).
- [x] T005 Implement the seven policies over one replay (FR-001).
- [x] T006 Implement the twelve metrics and the mark-out (FR-004 to FR-008).
- [x] T007 Implement the ablations and the verdict (FR-009, FR-010, FR-013, FR-014).
- [x] T008 Implement the entry fingerprint and the duplicate refusal (FR-002, FR-003).
- [x] T009 Export it from `channelflow.research` and add the trace marker.
- [x] T010 Mutation-check twenty-three guards with the bounded runner, verifying every restore.
- [x] T011 Close the four the sweep found: the engine among its own rivals, the mark-out's costs, the two quantiles, and the profit factor.
- [x] T012 Record [[ADR-052]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T003, T005 |
| FR-002, FR-003 | T008 |
| FR-004 | T003, T006 |
| FR-005, FR-006 | T006, T011 |
| FR-007 | T001, T006, T011 |
| FR-008 | T006, T011 |
| FR-009, FR-010 | T007 |
| FR-011, FR-012 | T004 |
| FR-013 | T007, T011 |
| FR-014, FR-015 | T007 |
| SC-001, SC-003, SC-008 | T003 |
| SC-002 | T008 |
| SC-004 to SC-007 | T006, T011 |
| SC-009 to SC-011 | T004, T007 |
| SC-012 to SC-014 | T007, T011 |
| SC-015 | T007 |

## Notes

Two of T011's four survivors were fixture blindness. Nothing pinned that the
"best simpler policy" excludes the engine — with the engine in its own rival
list it is the best of them by construction and the margin is zero — and nothing
asserted that the median and the 95th-percentile stop distance are two different
numbers.

The third was a mutation aimed at the wrong line. The mark-out's adverse
slippage was applied after the gross move had already been computed, so with a
zero fee it changed nothing; moved to the line that reads the price, it changes
the result and the test catches it. The test now pins both halves: slippage
changes nothing and a fee lowers the number.

The fourth was the profit factor over no losses, which the fixture never
produced a case for until the engine's own arm — every trade a winner — was
asserted on directly.

T001 also fixed a defect rather than adding a feature. `PricePoint` has carried
`data_quality_ok` since the replay was written, `StopPolicy.propose` has always
accepted one, and the replay never passed it — so §44A.18's freeze could not
fire on any replayed path.
