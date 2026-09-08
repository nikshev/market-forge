---
description: "Task list for REQ-WP-007 signal state machine"
---

# Tasks: Signal state machine

**Tests**: Written first. Pure.

## Phase 1: Lifecycle (US1)

- [x] T001 Write failing tests in `test_lifecycle.py`: a constructed approach-touch-reject-confirm sequence produces exactly that path; the same bars twice give identical paths and transition records; no transition skips a step (SC-001, SC-002, SC-007). Marker `@pytest.mark.trace("REQ-WP-007")`. Confirm RED.
- [x] T002 Implement `models.py`: `CandidateState`, an immutable `Transition` carrying its bar and reason, and a `Candidate` holding direction, boundary and history (FR-001, FR-003, FR-008, FR-016).
- [x] T003 Implement the transition table in `machine.py` for families A to D, with zone membership from channel position (FR-002, FR-005, FR-006, FR-007).

## Phase 2: Preconditions and invalidation (US2)

- [x] T004 Write failing tests in `test_preconditions.py`: a channel below the quality minimum opens nothing; a channel whose slope opposes the direction opens nothing; quality collapse and an outer-tolerance close each invalidate with a recorded reason (SC-003, SC-004, FR-009, FR-010). Confirm RED.
- [x] T005 Implement the opening preconditions (FR-004).
- [x] T006 Implement invalidation, and the missing-snapshot rule that nothing opens or advances without a channel (FR-015).

## Phase 3: Termination and plugins (US3)

- [x] T007 Write failing tests in `test_termination.py`: expiry after the configured bars; an expired candidate does not revive; a second detector registers without touching the machine (SC-005, SC-006, SC-008). Confirm RED.
- [x] T008 Implement expiry and the no-revival rule (FR-011, FR-012).
- [x] T009 Implement the rejection-detector protocol and close-back-inside (FR-013).
- [x] T010 Make every threshold a constructor argument (FR-017).

## Phase 4: Close

- [x] T011 Mutation-check three behaviours: allow a skipped step, drop the quality precondition, and let an expired candidate revive. Each must fail a test.
- [x] T012 Add `# @trace: REQ-WP-007` to each new source file.
- [x] T013 `make lint`, `make typecheck`, `make test` green.

## Notes

FR-007 — no skipped steps — is the one worth mutation-checking hardest. A state
machine that can jump from touch to confirmed produces signals that never
rejected, and they would look identical to real ones in every downstream record.
