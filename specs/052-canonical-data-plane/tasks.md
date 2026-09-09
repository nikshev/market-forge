---
description: "Task list for REQ-STORE-001"
---

# Tasks: Canonical Parquet data plane

- [x] T001 Add `pyarrow` and `duckdb`; declare the mypy overrides they need and say why stubs are not written.
- [x] T002 Implement the object-store port, its S3 adapter and a test double (FR-014).
- [x] T003 Implement the typed schema, its fingerprint and its canonical row encoding (FR-007, FR-015).
- [x] T004 Implement the snapshot, its content hash and its manifest (FR-006, FR-008, FR-009, [[ADR-053]]).
- [x] T005 Implement the table: the chain, the atomic commit, the reads (FR-001 to FR-005, FR-010, FR-011).
- [x] T006 Implement bounded DuckDB extracts (FR-012, FR-013).
- [x] T007 Write the unit tests, including a deterministic commit race and the import-isolation checks.
- [x] T008 Write the integration tests against MinIO — the conditional write in particular (SC-013).
- [x] T009 Mutation-check twenty-five guards with the bounded runner, verifying every restore.
- [x] T010 Act on what the sweep found: correct the zero-padding claim in the code and in its test.
- [x] T011 Record [[ADR-053]]; statuses, markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-005 | T005, T007 |
| FR-006 to FR-009 | T004, T007 |
| FR-010, FR-011 | T005, T007 |
| FR-012, FR-013 | T006, T007 |
| FR-014 | T002, T007, T008 |
| FR-015, FR-016 | T007 |
| SC-001 to SC-004 | T007 |
| SC-005 to SC-008 | T007 |
| SC-009 to SC-012 | T007 |
| SC-013 | T008 |
| SC-014, SC-015 | T007 |

## Notes

T009's sweep caught twenty-four of twenty-five. The one that survived is the
useful one: removing the zero-padding from manifest version keys changed no
test, because `snapshot_ids` parses each version and sorts the integers rather
than relying on the listing's lexical order.

The code and its test both claimed the opposite — that the padding was what made
a lexical listing a numeric ordering. Both now say what is true: the padding is
kept for the humans and tools that browse the bucket and do sort lexically, and
it is not what makes the chain correct. T010 is that correction, and it is the
whole reason the mutation was worth running.

The commit race in T007 needed a store wrapper. A real race needs two writers
that read the same current snapshot and then both commit the next version, and
sequentially the second writer re-reads and picks a later one. The collision has
to be injected at the only instant it can happen: between computing the version
and writing its manifest.
