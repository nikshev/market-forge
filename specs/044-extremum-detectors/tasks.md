---
description: "Task list for REQ-EXP-011"
---

# Tasks: Structural extremum detector comparison

- [x] T001 Add `channel_width_pct` to `DirectionalChangeDetector.on_bar` and thread it to the threshold policy.
- [x] T002 Fix the policy's channel-width units to match `ChannelSnapshot.width_pct`, and update its test.
- [x] T003 Write failing tests for the shape: five methods, a silent one reporting, the channel mode unavailable without a model (SC-001 to SC-003).
- [x] T004 Implement `extremum_detectors.py` (FR-001 to FR-006, FR-010 to FR-012).
- [x] T005 Implement and test the regime split and attribution (FR-007 to FR-009).
- [x] T006 Mutation-check ten guards with the bounded runner, verifying every restore.
- [x] T007 Close the six the sweep found: the median split, regime attribution, the ratio's direction, the lag, the costs, and the channel width's provenance.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002 | T003, T004 |
| FR-003, FR-004 | T001, T002, T007 |
| FR-005, FR-006 | T004, T007 |
| FR-007 to FR-009 | T005, T007 |
| FR-010 | T004, T007 |
| FR-011, FR-012 | T004 |
| SC-001 to SC-003 | T003 |
| SC-004 | T007 |
| SC-005, SC-006 | T007 |
| SC-007 to SC-009 | T007 |
| SC-010 to SC-012 | T004, T007 |

## Notes

T007's last fix needed a different fixture. A smooth sine turns twice per period
whatever the threshold, so it cannot tell a sensible threshold from an absurdly
small one — every method reports the same rate. Adding a chop makes the
difference visible: 45 confirmations per thousand bars against 235.
