---
description: "Task list for REQ-EXP-009"
---

# Tasks: Forecast corridor calibration

- [x] T001 Add `slope_log_per_bar` to `ChannelSnapshot` and set it in all four baselines, converting the quantile fitter's scaled slope back to per-bar.
- [x] T002 Write failing tests for the shape: three methods, an unsupported target refused, a short series refused (SC-001, SC-008).
- [x] T003 Implement `corridor_calibration.py` (FR-001 to FR-003, FR-007 to FR-010).
- [x] T004 Extract `pick_winner` and write the stability tests on constructed results (SC-004 to SC-007).
- [x] T005 Write the projection test: a trending series must not lose coverage (SC-002).
- [x] T006 Mutation-check ten guards with the bounded runner, verifying every restore.
- [x] T007 Make the per-instant measurements public and pin the conformal method's reaction instant (SC-009); add the per-fold spread test (SC-003).
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T002 |
| FR-002 | T001, T005 |
| FR-003 | T007 |
| FR-004 to FR-006 | T004 |
| FR-007, FR-009, FR-010 | T002, T003 |
| FR-008 | T007 |
| SC-001, SC-008 | T002 |
| SC-002 | T005 |
| SC-003, SC-009 | T007 |
| SC-004 to SC-007 | T004 |
| SC-010 | T003 |

## Notes

T007 came out of the sweep. Two mutations survived — pooling the folds, and
letting the conformal method calibrate on its own outcome — and neither could be
seen from the aggregate report. Publishing the per-instant measurements is what
made the second observable at all.
