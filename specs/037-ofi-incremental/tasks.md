---
description: "Task list for REQ-EXP-004"
---

# Tasks: OFI incremental value

- [x] T001 Register PRD §19's missing channel features and add channels to the exposed enumeration, with tests (SC-009).
- [x] T002 Make the ablation's taxonomy injectable, keeping REQ-US-006's four as the default.
- [x] T003 Write failing tests for the arms: five, cumulative, each adding one family (SC-001, SC-002).
- [x] T004 Write failing increment tests: named baseline and added features, absent over an unscored arm (SC-003, SC-005).
- [x] T005 Implement `ofi_incremental.py` (FR-001 to FR-008, FR-010, FR-011).
- [x] T006 Resolve membership from the registry, importing the producers first (FR-008, FR-009).
- [x] T007 Mutation-check ten guards with the bounded runner, verifying every restore.
- [x] T008 Close the three the sweep found: the increment's sign, the cold registry, and the vacuous `all()` over an empty family.
- [x] T009 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002 | T003, T004 |
| FR-003 | T008 |
| FR-004 to FR-006 | T004, T005 |
| FR-007 | T002 |
| FR-008, FR-009 | T006, T008 |
| FR-010, FR-011 | T005 |
| SC-001 to SC-003 | T003, T004 |
| SC-004 | T008 |
| SC-005 to SC-008 | T004, T005 |
| SC-009, SC-010 | T006, T008 |
| SC-011 | T005 |

## Notes

T008's third fix is the one to remember: `all(name.startswith("ofi_") for name in
found["ofi"])` is true when `found["ofi"]` is empty, so a membership rule that
matched nothing satisfied the shape assertion while emptying the arm it defines.
The fix is one line — assert non-empty first — and the failure mode is general.
