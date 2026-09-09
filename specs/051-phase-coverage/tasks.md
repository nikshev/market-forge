---
description: "Task list for the eleven REQ-PHASE-* notes"
---

# Tasks: Phase coverage and the last derived acceptance criteria

- [x] T001 Derive acceptance criteria for Phases 5, 6 and 8 from §17, §24/§25/§35/§41 and §32/§33/§34/§36; record the derivation and its exclusions.
- [x] T002 Survey the codebase against every phase's deliverable list.
- [x] T003 Add `covers:` and `not_delivered:` to all eleven notes, with a `## Coverage` section carrying the same two lists in prose.
- [x] T004 Write the coverage tests: both lists present, every covering requirement implemented, no gap list on an implemented phase.
- [x] T005 Write the completeness test and the marker scan.
- [x] T006 Move every phase from `draft` to `planned`; update `CLAUDE.md` and the vault index.
- [x] T007 All gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002 | T001 |
| FR-003 | T005 |
| FR-004 to FR-006 | T003, T004 |
| FR-007 | T005 |
| FR-008 | T002, T006 |
| SC-001 to SC-003 | T001, T005 |
| SC-004 to SC-006 | T003, T004 |
| SC-007, SC-008 | T005, T006 |

## Notes

T002 is the task that decided the outcome. The survey found a gap in every
single phase, including Phase 0: there is no virtual clock, no event bus
abstraction and no ClickHouse connectivity, though the rest of the skeleton is
there. Phase 8 has nothing at all.

That is why all eleven notes are `planned` rather than a mix. The alternative
readings — `implemented` for the phases whose work packages are all built — each
required treating a named deliverable as optional, and the PRD does not offer
that reading anywhere.
