---
traces: [REQ-WP-069]
status: draft
---

# Feature Specification: Three lists, not one

**Feature Branch**: `wp-069-phase-accounting`

**Created**: 2026-09-14

**Status**: Draft

**Input**: REQ-WP-069 — what a phase note says it has not done.

## Context

`not_delivered:` held three kinds of thing at once. Phase 4's entries were work
nobody had done, work waiting on Curve to publish source, and work an ADR had
deferred — so the phase could not reach `implemented` however much of it was
finished, and the list stopped answering what was left to do.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A phase closes on what it controls (Priority: P1)

**Acceptance**: `implemented` requires an empty `not_delivered:`; `blocked:` and
`deferred:` may hold entries.

### User Story 2 - Relabelling costs something (Priority: P1)

**Acceptance**: a `blocked:` entry naming no blocker fails; a `deferred:` entry
naming no ADR, or one that does not exist, fails.

### User Story 3 - A missing list is not an empty one (Priority: P2)

**Acceptance**: all three lists are required on every phase note.

### Edge Cases

- `[[ADR-999]]` matches the pattern and defers to nothing.
- "blocked" with no blocker is "not started" renamed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Three lists, all required.
- **FR-002**: `implemented` requires `not_delivered:` empty.
- **FR-003**: Every `blocked:` entry names what it waits on.
- **FR-004**: Every `deferred:` entry names an ADR file that exists.
- **FR-005**: The guards are functions, tested against bad input.

### Key Entities

- **check_blocked**, **check_deferred**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Phase 4's three entries land one per list.
- **SC-002**: Each guard rejects a synthetic bad entry and accepts a good one.
- **SC-003**: All eleven phase notes carry all three lists.

## Assumptions

- Blockers are prose; "waits on" and "waiting on" are the two spellings checked.

## Open Questions

- None.
