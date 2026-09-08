---
description: "Task list for REQ-WP-019 (criteria 4 and 5) and REQ-NRT-F"
---

# Tasks: Turning-point baselines and the GMDH derivative experiment

- [ ] T001 Write failing `test_path.py`: `P_hat`, `dP/dh` and `d2P/dh2` against hand arithmetic; roots against a hand-solved quadratic; curvature classification; a zero-curvature root producing no candidate; two roots both returned; a linear path producing none (SC-004, SC-005, FR-004 to FR-007).
- [ ] T002 Implement `path.py`.
- [ ] T003 Write failing `test_roots.py`: the three §13A.12 metrics recorded on every assessment; identical across repeated runs; a root present in only some members refused with the condition named; curvature below the minimum refused; thresholds are configuration (SC-006, SC-007, FR-008 to FR-011).
- [ ] T004 Implement `roots.py`.
- [ ] T005 Write failing `test_direct.py`: per-fold and aggregate metrics; a signal-free target reporting it does not beat the base rate; a missing feature refused; no fold fitted and scored on one row (SC-001 to SC-003, FR-001 to FR-003).
- [ ] T006 Implement `direct.py`.
- [ ] T007 Add `GMDHNetwork.predict` and make `predict_proba` clip it; confirm REQ-WP-018's tests still pass unchanged.
- [ ] T008 Write failing `test_experiment.py`: `NO_EDGE` on signal-free data with nothing raised; `NO_EDGE` when the base rate is not beaten whatever the roots did; rejected roots reported with reasons; too little data reported as a verdict (SC-008, SC-009, FR-012 to FR-014).
- [ ] T009 Implement `experiment.py`.
- [ ] T010 Assert no module consults a clock or an RNG (FR-015, SC-010).
- [ ] T011 Mutation-check the guards with the bounded runner, verifying every restore and sweeping the tree afterwards.
- [ ] T012 [[ADR-041]], [[ADR-042]], and an ADR superseding [[ADR-023]]'s "stops at `tested`".
- [ ] T013 Statuses: REQ-WP-019 to `implemented`, REQ-NRT-F off `draft`. Markers, all gates green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-003 | T006 |
| FR-004 to FR-007 | T002 |
| FR-008 to FR-011 | T004 |
| FR-012 to FR-014 | T009 |
| FR-015 | T010 |
| SC-001 to SC-003 | T005 |
| SC-004, SC-005 | T001 |
| SC-006, SC-007 | T003 |
| SC-008, SC-009 | T008 |
| SC-010 | T010 |

## Notes

T012 is not bookkeeping. [[ADR-023]] recorded a deliberate decision to leave a
work package below `implemented`, and the note that lifts it has to say what
changed — otherwise the graph shows a status moving with no reason attached to
it.
