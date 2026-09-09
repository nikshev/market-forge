---
description: "Task list for REQ-EXP-005"
---

# Tasks: Volume profile confluence

- [x] T001 Write failing classification tests over a profile with a deliberate shelf: a node, a value-area edge, neither, and the band's effect (SC-001, SC-002).
- [x] T002 Write failing study tests for all three verdicts and for the effect size changing one (SC-003, SC-004).
- [x] T003 Write failing refusal tests: small population, nothing decided, negative effect size (SC-006, SC-007, SC-010).
- [x] T004 Implement `volume_confluence.py` (FR-001 to FR-011).
- [x] T005 Assert the effect size has no default, over the signature (SC-005).
- [x] T006 Write the timeout and ambiguity tests (SC-008, SC-009).
- [x] T007 Mutation-check eleven guards with the bounded runner, verifying every restore.
- [x] T008 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003 | T001 |
| FR-004, FR-005 | T006 |
| FR-006 | T006 |
| FR-007 | T002 |
| FR-008 | T005 |
| FR-009 to FR-011 | T003 |
| SC-001, SC-002 | T001 |
| SC-003, SC-004 | T002 |
| SC-005 | T005 |
| SC-006, SC-007, SC-010 | T003 |
| SC-008, SC-009 | T006 |

## Notes

T001's control price had to move. 102.5 sat inside a thin bin, which is a
low-volume node — a level EXP-005 counts, and the classifier was right to say
so. The control is now a price where nothing traded at all.
