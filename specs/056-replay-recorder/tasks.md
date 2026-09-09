---
description: "Task list for REQ-PIPE-001"
---

# Tasks: A replay writes to the canonical plane

- [x] T001 Add two optional observers to `BacktestRunner`, defaulting to none.
- [x] T002 Write the channel recorder and the signal recorder, both buffering.
- [x] T003 Write `record_bars`: trades through the builder's own hook into the table.
- [x] T004 Write `record_replay`: snapshots and signals, on a copy of the caller's runner.
- [x] T005 Give the result a dataset identity over the tables it filled.
- [x] T006 Write the tests, including the loop through the durable repository.
- [x] T007 Mutation-check ten guards with the bounded runner, verifying every restore.
- [x] T008 Close what the sweep found: the final-state assertion and the unreachable guard.
- [x] T009 Statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002 | T003, T006 |
| FR-003 | T002, T004, T006 |
| FR-004 | T002, T008 |
| FR-005 to FR-007 | T004, T006 |
| FR-008, FR-009 | T005, T008 |
| FR-010, FR-011 | T006 |
| SC-001 to SC-003 | T006 |
| SC-004 | T008 |
| SC-005 to SC-011 | T006 |

## Notes

T008 closed two survivors and one of them was a design fault rather than a
missing test.

`_recording` skipped a table with no snapshot, and the caller had already
filtered those out — so the guard was unreachable and a mutation removing it
changed nothing. Two places decided the same thing and only one of them could
ever be wrong. The caller now passes every table the replay could have touched,
the bars table included, and the guard decides against the store. A counter and
a table can disagree; the table is the one a reader opens.

The other was a weak assertion. "Every stored signal has at least one
transition" passes when the recorder keeps the *first* state of each candidate
instead of the last — one transition per signal, and a recorder that looks like
it works. The stored histories now have to sum to the report's transition count.
