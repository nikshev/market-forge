---
description: "Task list for REQ-WP-011 OFI/LOB features"
---

# Tasks: OFI / LOB features

**Tests**: Written first. Every expected value hand-computed and written as a
literal — a feature checked against a second implementation of its own formula
passes whenever both are wrong the same way.

## Phase 1: The registry (US5)

First, so it is the shape each feature fits rather than a record of what got
built. ADR-015's gate depends on that order.

- [x] T001 Write failing `test_registry.py`: every exposed feature has an entry; no required field of PRD §19 is blank; an unregistered feature fails by name (SC-007). Marker `@pytest.mark.trace("REQ-WP-011")` and `@pytest.mark.trace("REQ-PRIN-008")`. Confirm RED.
- [x] T002 Implement `registry.py`: `FeatureSpec` with §19's sixteen fields, and `REGISTRY` keyed by name (FR-017, FR-018).

## Phase 2: Instant book features (US1)

- [x] T003 Write failing `test_instant.py`: QI at the touch; depth imbalance over 1/5/10/20/50 levels and ±5/10/25/50 bps; microprice below the mid when the ask queue dominates and equal to it when queues match; every one refuses on an invalid or un-bootstrapped book (SC-001, SC-002, SC-009). Confirm RED.
- [x] T004 Implement `instant.py` (FR-001 to FR-005) and register its features.

## Phase 3: Order flow imbalance (US2)

- [x] T005 Write failing `test_ofi.py`: Cont increments against hand arithmetic for each of the four price/size cases; window totals over 1s/5s/30s/1m/bar; an empty window reports zero observations; no increment across a gap (SC-003, SC-004). Confirm RED.
- [x] T006 Implement `ofi.py` (FR-006 to FR-009) and register `ofi_1s`, `ofi_5s`, `ofi_30s`, `ofi_1m`, `ofi_bar`.

## Phase 4: Trade flow (US3)

- [x] T007 Write failing `test_flow.py`: delta as signed notional; unknown aggressor counts in volume and in neither side; cumulative sum; slope and acceleration; normalized delta absent rather than zero on an empty window; out-of-order trades refused (SC-005). Confirm RED.
- [x] T008 Implement `flow.py` (FR-010 to FR-012) and register its features. No divergence feature — ADR-013.

## Phase 5: Wall lifecycle (US4)

- [x] T009 Write failing `test_walls.py`: a level anomalous against its neighbours becomes a wall; refill increments rather than restarting; the executed/cancelled split with executed bounded by volume traded at that price; a finalized record is never rewritten (SC-006). Confirm RED.
- [x] T010 Implement `walls.py` (FR-013 to FR-016) and register its features.

## Phase 6: Close

- [x] T011 Mutation-check the five guards that carry weight: compute an OFI increment across a gap; let a feature answer from an invalid book; attribute a wall's whole decrease to execution; drop a feature's registration; use ingest time for a window boundary. Each must fail a named test.
- [x] T012 Assert over the source that no module in the package consults a clock (SC-008).
- [x] T013 Confirm `# @trace: REQ-WP-011` on every new source file, and `# @trace: REQ-PRIN-008` on `registry.py`.
- [x] T014 `make lint`, `make typecheck`, `make test`, `make validate` green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-005 | T004 |
| FR-006 to FR-009 | T006 |
| FR-010 to FR-012 | T008 |
| FR-013 to FR-016 | T010 |
| FR-017, FR-018 | T002 |
| FR-019 | T012 |
| FR-020 | T002 — the registration states it; T011 checks the one place it could break |
| SC-001, SC-002, SC-009 | T003 |
| SC-003, SC-004 | T005 |
| SC-005 | T007 |
| SC-006 | T009 |
| SC-007 | T001 |
| SC-008 | T012 |

## Notes

T011's third mutation is the one worth the effort. ADR-014's split is an
estimate, and an estimate that silently became "all of it was executed" would
still produce plausible numbers — a wall that was pulled would read as absorbed
demand, which PRD §2.2 names as the failure mode this whole family exists to
avoid.
