---
description: "Task list for REQ-STORE-002"
---

# Tasks: The API's reads from the canonical plane

- [x] T001 Add `float_list`, `string_list` and `float_map` to the plane, with their canonical encodings.
- [x] T002 Write `rows.py`: reading one stored value, or refusing across kinds.
- [x] T003 Map §29.6's `channel_snapshots`, quality components and forecast array included.
- [x] T004 Map §29.7's `signals` plus a `signal_transitions` child table.
- [x] T005 Map §29.5's long-form `feature_snapshots`, plus `markets`, `setup_scores` and `score_contributions`.
- [x] T006 Implement `LakehouseRepository` over all seven tables.
- [x] T007 Write the conformance suite and parametrise the existing endpoint tests over both implementations.
- [x] T008 Mutation-check seventeen guards with the bounded runner, verifying every restore.
- [x] T009 Close what the sweep found: the score join, the latest-score tie-break, and four properties no endpoint can reach.
- [x] T010 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T003 to T006 |
| FR-002, FR-003 | T007 |
| FR-004, FR-005 | T003, T007 |
| FR-006 | T004, T009 |
| FR-007 | T004, T007 |
| FR-008, FR-009 | T005, T009 |
| FR-010, FR-011 | T006, T007 |
| FR-012 | T002, T009 |
| SC-001 to SC-004 | T007 |
| SC-005 to SC-007 | T009 |
| SC-008 to SC-010 | T007, T009 |

## Notes

T008 found a real bug, which is the second time a sweep has done so today rather
than merely confirming the tests.

A score's contributions were joined to it on `as_of_ns`. Scores tie on that
instant whenever the caller does not supply one — which is the default — so a
market with two scores gave back a score carrying every group either of them
had. Every row involved was correct; the join was not. Scores now carry a
content-derived id and the contributions join on it.

The same default exposed a second, smaller one: `max` returns the *first*
maximal element, so the "latest score" of a tied group was the oldest. The
reader takes the last of the newest now, which is what append-only means.

Four of the five survivors were properties no endpoint can reach — the feature
row order (which exists for the content hash), the transition ordinal (which
matters only when rows arrive out of order), and the two row-helper refusals.
They are tested directly in `tests/unit/tables/test_mapping.py`.
