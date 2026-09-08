---
description: "Task list for REQ-WP-013 and REQ-BIAS-005"
---

# Tasks: Derivatives feature engine

## Phase 1: State and the settlement boundary (US1)

- [ ] T001 Write failing `test_state.py` and `test_funding.py`: the as-of join never returns a later state and refuses an unbreakable tie; an unsettled funding rate is not used at `t`; a z-score refuses on too few observations and on a constant series (SC-001, SC-002, SC-006). Markers for `REQ-WP-013` and `REQ-BIAS-005`. Confirm RED.
- [ ] T002 Implement `state.py` — the join, and the shared z-score (FR-002, FR-003, FR-010).
- [ ] T003 Implement `funding.py` (FR-001, FR-004).

## Phase 2: Open interest and basis (US2, US3)

- [ ] T004 Write failing `test_openinterest.py`: changes over windows; z-score; OI-to-volume ratio absent on zero volume; each of PRD §16.2's four regimes; basis and premium against hand-computed values; absent when a leg is missing (SC-003, SC-004). Confirm RED.
- [ ] T005 Implement `openinterest.py` (FR-005 to FR-008).

## Phase 3: Liquidations (US4)

- [ ] T006 Write failing `test_liquidations.py`: long and short notional separate; imbalance absent when both are zero; intensity against volume; clusters by price bucket; time since the last spike (SC-005). Confirm RED.
- [ ] T007 Implement `liquidations.py` (FR-009).

## Phase 4: Registry and close

- [ ] T008 Register every feature and extend `exposed_feature_names()` to read this package, so ADR-015's gate covers it (FR-011, SC-007).
- [ ] T009 Assert no module consults a clock (FR-012, SC-008).
- [ ] T010 Mutation-check five guards: use an unsettled funding rate; let the z-score return zero on a constant series; take a later state in the join; return an infinite ratio; drop a feature's registration. Verify every restore.
- [ ] T011 Confirm `# @trace:` markers; set `REQ-WP-013` and `REQ-BIAS-005` to `implemented`.
- [ ] T012 `make lint`, `make typecheck`, `make test`, `make validate` green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-004 | T003 |
| FR-002, FR-003, FR-010 | T002 |
| FR-005 to FR-008 | T005 |
| FR-009 | T007 |
| FR-011 | T008 |
| FR-012, FR-013 | T009 |
| SC-001, SC-002, SC-006 | T001 |
| SC-003, SC-004 | T004 |
| SC-005 | T006 |
| SC-007 | T008 |

## Notes

T008 is the task that keeps ADR-015 honest. The registry test compares exposed
against registered, and `exposed_feature_names()` currently reads only
REQ-WP-011's package — so a second package could ship unregistered features and
the gate would still pass. Extending the enumeration is what makes the gate
about the system rather than about one module.
