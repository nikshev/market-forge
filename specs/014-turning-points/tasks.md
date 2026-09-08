---
description: "Task list for REQ-WP-019 and REQ-NRT-A..E"
---

# Tasks: Causal turning points

**Tests**: Written first. Every expected timestamp hand-identified in the
fixture series.

## Phase 1: The two timestamps (US1)

- [ ] T001 Write failing `test_directional_change.py`: a series peaking then reversing confirms with `extremum_time` at the peak and `known_at` at the crossing bar; the lag is the bar count; a peak that never reverses confirms nothing; `known_at >= extremum_time` always (SC-001, SC-002). Markers `@pytest.mark.trace("REQ-WP-019")` and `@pytest.mark.trace("REQ-NRT-C")`. Confirm RED.
- [ ] T002 Implement `models.py` — §13A.19's `ExtremumCandidate` and `ConfirmedExtremum`, frozen, refusing `known_at < extremum_time` (FR-001, FR-002, FR-009).
- [ ] T003 Implement `detector.py`'s directional-change state machine (FR-003, FR-004).

## Phase 2: Adaptive thresholds (US2)

- [ ] T004 Write failing `test_thresholds.py`: each of §13A.5's five modes against hand-computed values; the hybrid is the maximum and never below the floor; a threshold at `t` uses only data at or before `t`; too little history refuses rather than approximating (SC-003). Confirm RED.
- [ ] T005 Implement `thresholds.py` (FR-005, FR-006).

## Phase 3: Prominence (US3)

- [ ] T006 Write failing `test_prominence.py`: a sub-threshold swing is not confirmed; two extrema too close together are rejected; prominence is reported in bps and ATR (SC-004). Confirm RED.
- [ ] T007 Implement `prominence.py` and wire it into the detector (FR-007, FR-008).

## Phase 4: The mandatory tests (US4)

The deliverable, not a checking step.

- [ ] T008 Write failing `test_non_repainting.py` — Test A, future-bar invariance: outputs up to `t`, random bars appended, every field of every prior output unchanged; the outputs must be non-empty first, or the comparison is vacuous (SC-005). Confirm RED.
- [ ] T009 Test B, candidate chronology: an invalidated candidate's original record is unchanged; invalidation appends (SC-006, FR-010).
- [ ] T010 Test C, confirmation legality: `known_at >= extremum_time`, and no input to a confirmation carries `available_at > known_at` (SC-007).
- [ ] T011 Test D, centered filter prohibition: implement `causality.py` and assert the production path refuses a transform declaring `centered=True`; assert the source imports no centered helper (SC-008, FR-011).
- [ ] T012 Test E, replay parity: one stream replayed matches the live run exactly (SC-009).
- [ ] T013 Assert no module in the package consults a clock (SC-010, FR-012).

## Phase 5: Close

- [ ] T014 Mutation-check the five guards: let a confirmation backdate `known_at`; recompute the threshold from current data; drop the prominence filter; let a centered transform through; make a record mutable. Each must fail a named test.
- [ ] T015 Confirm `# @trace:` markers for REQ-WP-019 and each REQ-NRT-* on the module or test that satisfies it.
- [ ] T016 Set `REQ-NRT-A` to `E` to `implemented`; set `REQ-WP-019` to `tested` and no further (ADR-023).
- [ ] T017 `make lint`, `make typecheck`, `make test`, `make validate` green.

## Coverage

| | Task |
| --- | --- |
| FR-001, FR-002, FR-009 | T002 |
| FR-003, FR-004 | T003 |
| FR-005, FR-006 | T005 |
| FR-007, FR-008 | T007 |
| FR-010 | T009 |
| FR-011 | T011 |
| FR-012 | T013 |
| FR-013 | T012 |
| FR-014 | T008 |
| SC-001, SC-002 | T001 |
| SC-003 | T004 |
| SC-004 | T006 |
| SC-005 to SC-010 | T008 to T013 |

## Notes

T008 is the one to get right. A future-bar invariance test that compares two
empty lists passes; so does one that compares only the count, or only the last
record. It appends *random* bars — a fixed appendix could be the one series a
broken detector happens to survive — asserts the prior outputs are non-empty,
and compares every field.

T016 is a task rather than a step because it is a judgement, and the tooling
will not make it: no validator rule reads acceptance criteria, so nothing would
object to marking REQ-WP-019 implemented.
