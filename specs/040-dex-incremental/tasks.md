---
description: "Task list for REQ-EXP-007"
---

# Tasks: DEX incremental value

- [x] T001 Extract the cumulative machinery from [[REQ-EXP-004]] into `cumulative.py`, leaving both experiments as taxonomies over it.
- [x] T002 Write failing tests for the arms and the instrument (SC-001, SC-006).
- [x] T003 Implement `dex_incremental.py` (FR-001 to FR-006, FR-008, FR-009).
- [x] T004 Write the failing registry-state tests: every DEX family empty, four arms not run (SC-004).
- [x] T005 Fix the divergence prefix, which was matching the perp-spot basis (SC-005, FR-007).
- [x] T006 Write the supplied-features tests, so the scoring path is exercised (SC-002, SC-003).
- [x] T007 Mutation-check nine guards with the bounded runner, verifying every restore.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 | T002 |
| FR-002 | T004 |
| FR-003, FR-004 | T006 |
| FR-005 | T002 |
| FR-006, FR-007 | T004, T005 |
| FR-008 | T002 |
| FR-009 | T006 |
| SC-001, SC-006, SC-007 | T002 |
| SC-002, SC-003 | T006 |
| SC-004, SC-005 | T004, T005 |
| SC-008 | T006 |

## Notes

T005 is the one to remember. `basis_` matched `basis_bps` — PRD §16's perp-spot
basis, which is a CEX feature — so the DEX divergence arm would have scored a
CEX number and reported its contribution as the DEX view's. The sweep caught it
because the registry-state test pins exactly which families are empty.
