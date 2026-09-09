---
description: "Task list for REQ-US-003"
---

# Tasks: Comparing the channel that existed against the model's later state

- [x] T001 Write failing `test_repaint_comparison.py`: both channels and every delta; the width-relative centre movement; a zero width reporting no ratio (SC-001, SC-002).
- [x] T002 Write failing tests for the hindsight span: stated, zero when the instants match, inverted refused (SC-004, SC-005).
- [x] T003 Write failing tests for the refusals: no stored snapshot, and a version difference reported rather than refused (SC-003, FR-011).
- [x] T004 Implement `comparison.py` (FR-001 to FR-008, FR-011).
- [x] T005 Write the research-only test and the import ban over the signal, alerting, stop and extrema packages (SC-006, SC-007, FR-009, FR-010).
- [x] T006 Add `ChannelComparisonOut` and `GET /channels/comparison`, with 422 for an inverted pair and 404 for a missing snapshot.
- [x] T007 Mutation-check seven guards with the bounded runner, verifying every restore.
- [x] T008 [[ADR-046]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-008, FR-011 | T004 |
| FR-009, FR-010 | T005 |
| SC-001, SC-002 | T001 |
| SC-003 | T003 |
| SC-004, SC-005 | T002 |
| SC-006, SC-007 | T005 |

## Notes

T001's fixture carries seventy bars because the production fitter's lookback is
sixty. A shorter history refuses the refit, and the comparison would have been
untested rather than proven — the first version of the fixture had ten.
