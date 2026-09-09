---
description: "Task list for REQ-REPRO-001 and REQ-BIAS-011"
---

# Tasks: Run identity, registry and reporting gate

- [x] T001 Implement the four-component identity, the two absences and the dirty-tree guard (FR-001 to FR-005).
- [x] T002 Implement config hashing and dataset composition (FR-006 to FR-008).
- [x] T003 Implement the registry as a lakehouse table, recording every outcome (FR-009, FR-010).
- [x] T004 Implement the reporting gate for both rules (FR-011, FR-012).
- [x] T005 Write the tests, including the clock and git import bans (FR-013).
- [x] T006 Extend the lakehouse isolation ban to this package — it sits on the plane and pulls the backends in behind it.
- [x] T007 Mutation-check twenty-seven guards with the bounded runner, verifying every restore.
- [x] T008 Close what the sweep found: the run hash's framing.
- [x] T009 Record [[ADR-054]] and amend [[ADR-024]]'s line about rule 11; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-005 | T001, T005, T008 |
| FR-006 to FR-008 | T002, T005 |
| FR-009, FR-010 | T003, T005 |
| FR-011, FR-012 | T004, T005 |
| FR-013 | T005 |
| SC-001 to SC-005 | T005, T008 |
| SC-006 to SC-008 | T005 |
| SC-009 to SC-011 | T005 |
| SC-012 to SC-014 | T005 |
| SC-015 | T005 |

## Notes

T007 found one real gap and two mutations that were not behavioural, and the
difference is worth recording because it recurs.

The real one: the run hash concatenated its components without framing them, so
a run over dataset `ab` with config `c` hashed identically to one over dataset
`a` with config `bc`. T008 frames each component and a test pins the collision.

The two that were not: removing the integer type tag alone, or the string tag
alone, changes no hash — the remaining tag still separates the two encodings.
Removing *both* collides `60` with `"60"`, and
`test_a_number_written_as_a_string_is_not_the_same_config` catches that. The
property is tested; the single-tag mutations simply were not mutations. The
sweep is reported as twenty-seven attempted, twenty-six behavioural, all
twenty-six caught.
