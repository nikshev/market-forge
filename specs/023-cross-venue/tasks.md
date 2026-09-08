---
description: "Task list for REQ-WP-016"
---

# Tasks: Cross-venue engine

- [x] T001 Write failing `test_consensus.py` for the median: a hand-computed median over three venues, the contributors named, an even count reported as interpolated (SC-001, FR-001, FR-005).
- [x] T002 Write failing tests for exclusion and refusal: a stale venue, a missing mid, fewer than two contributors, venues quoting different assets (SC-002, SC-003, SC-004).
- [x] T003 Implement `models.py` — `VenueQuote` and `ExecutableQuote`, with their invariants at construction.
- [x] T004 Implement `consensus.py` — `consensus_mid`, `basis_bps`, `executable_basis_bps` (FR-001 to FR-008).
- [x] T005 Write failing tests for basis: the §17.3 formula, zero at the consensus, an AMM refused, executable basis at a notional, no default notional (SC-005, SC-006).
- [x] T006 Write failing `test_fragmentation.py`: depth at 10/25/50 bps, best venue by all-in cost where top-of-book disagrees, an unfillable venue excluded and named, concentration rising as liquidity gathers (SC-009, SC-010, FR-012 to FR-014).
- [x] T007 Implement `fragmentation.py` — `depth_table`, `best_execution_venue`, `concentration`.
- [x] T008 Write failing `test_leadlag.py`: returns over 1/5/10 seconds using only prices at or before the instant, a window reaching before the data start returning nothing, aligned lagged correlation, the research-only marking (SC-007, FR-009 to FR-011).
- [x] T009 Implement `leadlag.py`, and leave it out of `__init__.py` ([[ADR-040]]).
- [x] T010 Write the import-ban test over the signal, alerting and stop packages, plus the guard that those packages still exist (SC-008).
- [x] T011 Assert no module consults a clock (FR-016, SC-011).
- [x] T012 Mutation-check eight guards with the bounded runner, verifying every restore and sweeping the tree afterwards.
- [x] T013 Markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-008 | T004 |
| FR-009 to FR-011 | T009 |
| FR-012 to FR-014 | T007 |
| FR-015, FR-016 | T011 |
| SC-001, SC-005, SC-006 | T001, T005 |
| SC-002 to SC-004 | T002 |
| SC-007 | T008 |
| SC-008 | T010 |
| SC-009, SC-010 | T006 |
| SC-011 | T011 |

## Notes

T010 is the task the whole lead-lag section rests on. §17.2's prohibition is
about intent, and intent is not checkable; the import ban is the same
prohibition restated as a fact about the source tree, which is.
