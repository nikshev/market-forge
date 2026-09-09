---
description: "Task list for REQ-US-002"
---

# Tasks: The alert's link restores the chart it was sent about

- [x] T001 Write failing `test_deep_link_overlays.py`: the link names the declared layers, in a stable order; an alert declaring none omits the parameter; an unlisted name is refused (SC-001 to SC-003).
- [x] T002 Implement `alerting/overlays.py` with PRD §27.2's twelve layers, and add `Alert.overlays` (FR-001).
- [x] T003 Extend `chart_deep_link` with the sorted, deduplicated parameter (FR-002, FR-003).
- [x] T004 Write failing `overlays.test.ts` for reading the list back: restored, not recorded, unreadable, duplicates, and an empty list (SC-004, SC-005, FR-004 to FR-007).
- [x] T005 Implement `overlays.ts` and the `OVERLAYS`/`DEFAULT_OVERLAYS` vocabulary.
- [x] T006 Write failing tests for `visibleRangeFor`: centred, outside the history, at both edges, a history shorter than the window (SC-006, SC-007, FR-008 to FR-010).
- [x] T007 Implement `visibleRangeFor` and have `Chart` centre on the instant and draw only the layers that are on.
- [x] T008 Write failing `deepLinkOverlays.test.tsx`, then have `App` state the restoration when it is not exact (FR-005).
- [x] T009 Mutation-check both sides with the bounded runner, verifying every restore.
- [x] T010 [[ADR-045]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T002 |
| FR-002, FR-003 | T003 |
| FR-004, FR-006, FR-007 | T005 |
| FR-005 | T008 |
| FR-008 to FR-010 | T007 |
| SC-001 to SC-003 | T001 |
| SC-004, SC-005 | T004, T008 |
| SC-006, SC-007 | T006 |

## Notes

T006's short-history case was added after the sweep: with a window of sixty bars
and fixtures of twenty, the clamp on the upper end of the range was never the
thing that held it inside the data.
