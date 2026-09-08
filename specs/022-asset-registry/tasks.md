---
description: "Task list for REQ-ASSET-001"
---

# Tasks: Asset identity registry

- [x] T001 Write failing `test_registry.py` for identity: PRD §18.13's ETH example resolves to one asset; a shared ticker never merges two assets; a representation without a declared asset is refused; an ambiguous ticker lookup refuses (SC-001 to SC-004).
- [x] T002 Implement `models.py` — §18.13's entities, with per-entity invariants at construction (FR-001, FR-002, FR-007, FR-008, FR-010, FR-011, FR-012).
- [x] T003 Implement `registry.py` — registration, resolution and the cross-entity refusals (FR-003 to FR-006, FR-009, FR-013).
- [x] T004 Write failing tests for the three-state fields: not-applicable and unknown distinguishable, a provenance filter expressible, omission refused (SC-006).
- [x] T005 Write failing tests for wrapper chains: resolve to root, a wrapper of a wrapper resolves, a cycle refuses, a chain deeper than any real one refuses (SC-007).
- [x] T006 Write failing tests for venues and pairs: an on-chain venue without a deployment refuses, an order book with one refuses, a pair against itself refuses (SC-008, SC-009).
- [x] T007 Write failing tests for ordering: total and stable, ties broken by key, a missing confidence refused (SC-010).
- [x] T008 Mutation-check eight guards with a bounded runner, verifying every restore.
- [x] T009 Assert no module consults a clock or opens a socket (FR-014, SC-011).
- [x] T010 Markers, statuses, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002, FR-007, FR-008, FR-010 to FR-012 | T002 |
| FR-003 to FR-006, FR-009, FR-013 | T003 |
| FR-014 | T009 |
| SC-001 to SC-004 | T001 |
| SC-006 | T004 |
| SC-007 | T005 |
| SC-008, SC-009 | T006 |
| SC-010 | T007 |
| SC-011 | T009 |

## Notes

T008 uses a bounded runner. The GMDH sweep and this one both contain a mutation
whose removal produces no answer rather than a wrong one, and an unbounded
pytest call cannot tell that from a passing suite — it simply stops responding.
