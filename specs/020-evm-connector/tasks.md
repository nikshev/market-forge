---
description: "Task list for REQ-WP-014 and REQ-BIAS-006"
---

# Tasks: EVM connector

- [x] T001 Write failing `test_ledger.py`: availability filtering; the time ordering refusals; finality advancing at configured depths and never regressing; `SAFE`-only reads (SC-001, SC-002, SC-005).
- [x] T002 Implement `records.py` — §18.3's envelope and §18.4's ladder, with the ordering validated at construction (FR-001, FR-004, FR-017).
- [x] T003 Implement `ledger.py` — availability reads and finality advance (FR-002, FR-003, FR-008).
- [x] T004 Write failing reorg tests: an invalidation is emitted, the original is untouched, a read before the reorg still returns it, a finalized block refuses (SC-003, SC-004).
- [x] T005 Implement reorg orphaning (FR-005 to FR-007).
- [x] T006 Write failing `test_decoders.py`: registered decoding works; a mismatched ABI hash fails closed with the raw log retained; deployment ranges select versions (SC-006, SC-007).
- [x] T007 Implement `decoders.py` (FR-009 to FR-011).
- [x] T008 Write failing `test_providers.py`: health counts; cooldown on an error storm; the fastest healthy provider chosen; no healthy provider refuses; disagreements reported (SC-008, SC-009).
- [x] T009 Implement `providers.py` (FR-012 to FR-015).
- [x] T010 Mutation-check seven guards, verifying every restore.
- [x] T011 Assert no module consults a clock or opens a socket (FR-016, SC-010).
- [x] T012 Markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-004, FR-017 | T002 |
| FR-002, FR-003, FR-008 | T003 |
| FR-005 to FR-007 | T005 |
| FR-009 to FR-011 | T007 |
| FR-012 to FR-015 | T009 |
| FR-016 | T011 |
| SC-001, SC-002, SC-005 | T001 |
| SC-003, SC-004 | T004 |
| SC-006, SC-007 | T006 |
| SC-008, SC-009 | T008 |
| SC-010 | T011 |

## Notes

T010's second mutation is the one to watch: stamping `orphaned_at` with zero
rather than the reorg's instant deletes the record from every read, including
reads of instants before the reorg. That is the failure ADR-033 is about, and
it looks like correct cleanup.
