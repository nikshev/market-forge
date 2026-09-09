---
description: "Task list for REQ-EXP-001"
---

# Tasks: Channel model comparison

- [x] T001 Add `bands="std"` to baseline A with its own model name (PRD §13.2's first width option).
- [x] T002 Add the `ChannelModel` protocol and widen the backtest runner to it.
- [x] T003 Write failing `test_channel_comparison.py` for the shape: five entries, one split, a refusal reported without stopping the run (SC-001).
- [x] T004 Write failing metric tests: coverage responds to band width and looks forward, stability is dispersion not average, a repaint is counted (SC-002 to SC-004).
- [x] T005 Implement `channel_comparison.py` (FR-001 to FR-008, FR-013, FR-014).
- [x] T006 Write failing expectancy tests: out-of-sample only, refused without costs, absent when nothing traded (SC-006 to SC-008).
- [x] T007 Implement the out-of-sample expectancy over [[REQ-BT-001]]'s outcomes and economics (FR-009 to FR-012).
- [x] T008 Mutation-check eleven guards with the bounded runner, verifying every restore.
- [x] T009 Strengthen the six tests the sweep found weak.
- [x] T010 [[ADR-049]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003 | T003, T005 |
| FR-004 to FR-008 | T004, T005 |
| FR-009 to FR-012 | T006, T007 |
| FR-013, FR-014 | T005 |
| SC-001 | T003 |
| SC-002 to SC-005 | T004, T009 |
| SC-006 to SC-008 | T006 |
| SC-009, SC-010 | T003 |

## Notes

T009 is more than half the test file. Six of eleven mutations survived the first
sweep, and every one of them was a fixture that could not tell two definitions
apart — coverage forwards from backwards, dispersion from average, a cost figure
from a fit count.
