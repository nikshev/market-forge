---
description: "Task list for REQ-WP-005 bar aggregation"
---

# Tasks: Bar aggregation

**Tests**: Written first. Pure — no services, no clock.

## Phase 1: The bar (US1)

- [x] T001 Write failing tests in `tests/unit/bars/test_bar_fields.py`: a known trade sequence produces a bar whose fourteen fields match; VWAP from a high-precision price is exact; out-of-order trades still yield open and close by event time (SC-001, SC-007, FR-003). Marker `@pytest.mark.trace("REQ-WP-005")`. Confirm RED.
- [x] T002 Implement `models.py`: `Bar`, frozen, with the fourteen fields PRD §12 names (FR-002).
- [x] T003 Implement accumulation in `builder.py`: OHLC by event time, the aggressive-side split, exact decimal aggregates, VWAP (FR-001, FR-004, FR-005).

## Phase 2: Finalization and the late-event policy (US2)

- [x] T004 Write failing tests in `test_finalization.py`: a trade belonging to a finalized bar leaves it byte-identical and raises the late counter; a trade inside the grace period is included; a watermark jump finalizes intervening windows in order (SC-002, SC-004, SC-005). Confirm RED.
- [x] T005 Implement the watermark and grace-period finalization (FR-006, FR-010, FR-012).
- [x] T006 Implement the late-event policy per ADR-005: discard and count, never amend (FR-008, FR-009).

## Phase 3: Delivery and determinism (US3)

- [x] T007 Write failing tests in `test_determinism.py`: shuffled trades produce identical bars; the callback fires exactly once per bar and not before (SC-003, FR-011, FR-013). Confirm RED.
- [x] T008 Implement the finalization callback (FR-011).
- [x] T009 Make timeframe and grace period constructor arguments, not constants (FR-014).

## Phase 4: Close

- [x] T010 Verify SC-006 by inspection and by signature: the builder takes no clock argument and no module in `bars/` imports `time` or `datetime.now`. Assert it with a test over the source, so it stays true.
- [x] T011 Add `# @trace: REQ-WP-005` to each new source file.
- [x] T012 Mutation-check the two load-bearing behaviours: allow a finalized bar to be amended, and derive the watermark from wall-clock. Each must fail a test.
- [x] T013 `make lint`, `make typecheck`, `make test` green.

## Notes

SC-006 is asserted rather than assumed. "The builder does not use wall-clock
time" is the kind of property that stays true until someone adds a convenience,
and a test over the source is what keeps it true.
