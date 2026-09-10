---
traces: [REQ-WP-026]
status: draft
---

# Feature Specification: A stale derivatives state is refused

**Feature Branch**: `wp-026-stale-derivatives`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-026 — PRD §45 Phase 3's second acceptance criterion.

## Context

Phase 3 states two acceptance criteria. The first holds: `state_at` never
returns a state later than the instant asked about. The second — "stale REST
polling cannot silently reuse old value" — does not: `state_at` returns the
newest state at or before the instant with no upper bound on its age.

A poll that failed, or a venue that stopped publishing, leaves the last value in
place. Funding, open interest and basis then report numbers that look current,
and every score built on them inherits the error without a trace.

The rest of the repository already knows this: `crossvenue` excludes a quote
past its tolerance and names why, `book` and `alerting` both guard it, and PRD
§43's ranker penalizes staleness in the score. The one package Phase 3's
criterion names is the one without it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An old value is refused, not returned (Priority: P1)

A read at an instant whose newest state is older than the tolerance fails,
naming the age and the tolerance.

**Why this priority**: This is the criterion. Everything else is shape.

**Acceptance Scenarios**:

1. **Given** a state within the tolerance, **When** it is read, **Then** it is returned.
2. **Given** a state older than the tolerance, **When** it is read, **Then** it is refused with its age and the tolerance in the message.
3. **Given** no state at all, **When** a read happens, **Then** the refusal is distinguishable from the stale one — a venue that never published and one that stopped are different facts.

---

### User Story 2 - Every feature inherits the rule (Priority: P1)

A feature derived from state does not re-check freshness and cannot forget to.

**Why this priority**: A rule each call site has to remember is a rule one call
site will forget — the reason `state_at` exists at all, in its own docstring.

**Acceptance Scenarios**:

1. **Given** a stale state, **When** any state-derived feature is computed, **Then** it is refused.
2. **Given** a new feature written later, **When** it reads state through the shared path, **Then** it is covered without doing anything.

---

### User Story 3 - The tolerance is the caller's (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a caller with a stated tolerance, **When** it reads, **Then** that tolerance decides.
2. **Given** a caller that states none, **When** it reads, **Then** a documented default applies — never an unbounded one.

### Edge Cases

- **A z-score window spanning old observations.** Untouched: the rule is about a value read as current, not the history behind it. Refusing old history would break the feature the rule protects.
- **A state exactly at the tolerance.** Fresh — the boundary is inclusive, and stating which way it falls is the point of saying so.
- **A tolerance of zero.** Only a state at exactly the instant asked about is fresh. Legal, extreme, and a caller's business.
- **A negative tolerance.** Refused: it describes no window.
- **A correction arriving later for the same instant.** Unchanged — the newest ingest still wins, and its age is measured from the event it describes rather than from when it arrived.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Reading state at an instant MUST take a maximum age.
- **FR-002**: A state older than the tolerance MUST be refused, naming its age and the tolerance.
- **FR-003**: A stale refusal MUST be distinguishable from an absent one.
- **FR-004**: The tolerance MUST be the caller's, with a documented default.
- **FR-005**: A negative tolerance MUST be refused.
- **FR-006**: A state exactly at the tolerance MUST be fresh.
- **FR-007**: Every state-derived feature MUST inherit the rule without re-checking it.
- **FR-008**: A z-score's history MUST NOT be constrained by the tolerance.
- **FR-009**: Which state wins at one instant MUST be unchanged.

### Key Entities

- **Tolerance**: how old a reading may be and still be presented as current.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A read one nanosecond past the tolerance is refused; one exactly at it is not.
- **SC-002**: The refusal message contains the age and the tolerance.
- **SC-003**: A stale refusal and an absent refusal are different types.
- **SC-004**: Every feature reading through the shared path refuses a stale state, with no per-feature check.
- **SC-005**: A z-score over a long window still computes when the newest state is fresh.
- **SC-006**: Which state wins among several at one instant is unchanged.

## Assumptions

- **Refusal, not exclusion.** `crossvenue` excludes a stale quote because it has others to fall back on; a single state has nothing to fall back to, so the honest answer is to refuse.
- **Age is measured from the event time**, not the ingest time. A correction that arrives late describes an old instant and is old.
- **A default is stated, not hidden.** Absent means infinite, and infinite makes the criterion vacuous.
- **Existing callers will break, and that is the finding rather than a cost.** A test whose fixture holds a state older than any sensible tolerance was asserting on a value the criterion says must not be used.
