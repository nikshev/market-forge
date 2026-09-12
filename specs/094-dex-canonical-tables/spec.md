---
traces: [REQ-WP-053]
status: draft
---

# Feature Specification: The DeFi primitives land on the canonical plane

**Feature Branch**: `wp-053-iceberg-defi-tables`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-053 — Phase 4's Iceberg DeFi tables.

## Context

PRD §18.12 asks adapters for common economic primitives and §6.4 makes Iceberg
the canonical history. The adapters have produced those primitives since
[[REQ-WP-015]] and nothing stores them.

Three of the four primitives have producers. `LiquidityState` does not, and is
not defined here: its `reconstruction_quality` describes a reconstruction nothing
performs, and a table nothing writes is a schema pretending to be a guarantee.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A primitive survives storage (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a swap, **When** written and read back, **Then** every field is identical.
2. **Given** a value beyond `int64`, **When** stored, **Then** it comes back whole.
3. **Given** a price `float64` cannot hold, **When** stored, **Then** every digit survives.
4. **Given** a signed amount, **When** stored, **Then** the sign survives.

---

### User Story 2 - Absent stays absent (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a swap nobody priced, **When** stored, **Then** its notional is absent, not zero.
2. **Given** a field with no producer, **When** the schema is inspected, **Then** the column is not there.
3. **Given** an absent value and a zero, **When** hashed, **Then** they are different datasets.

---

### User Story 3 - A curve becomes rows without losing its meaning (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a curve, **When** written, **Then** one row per band per side.
2. **Given** an unreachable band, **When** read, **Then** it is distinguishable from a cheap one.
3. **Given** both sides, **When** read, **Then** each keeps its own token.

### Edge Cases

- **A collect that moves no liquidity.** Still its own kind, not a zero-delta modify.
- **A point-in-time read.** Excludes what had not happened.
- **An empty flush.** Writes no snapshot.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Swaps, liquidity changes and depth curves MUST each have a canonical table.
- **FR-002**: A written row MUST read back identical.
- **FR-003**: Signs MUST survive.
- **FR-004**: Values beyond `int64` MUST survive.
- **FR-005**: Prices MUST keep every digit.
- **FR-006**: A field with no producer MUST be absent from the schema.
- **FR-007**: A sometimes-absent field MUST store as absent and hash differently from zero and from empty.
- **FR-008**: An unreachable band MUST be distinguishable from a reached one.
- **FR-009**: Depth amounts MUST stay in their own tokens.
- **FR-010**: A point-in-time read MUST exclude later rows.

### Key Entities

- **dex_swaps**, **dex_liquidity**, **dex_depth**: the three tables.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every field of each primitive round-trips.
- **SC-002**: A value above 2^63 and a price float64 cannot hold both survive.
- **SC-003**: Five named §18.12.1 fields are absent from the schema.
- **SC-004**: An absent value, a zero and an empty string are three datasets.
- **SC-005**: No test needs a service beyond a temporary warehouse.

## Assumptions

- **`LiquidityState` waits for a producer.** Defining it now would be a schema
  pretending to be a guarantee.
- **The band is a column, not a set of columns.** §18.12.3 says the grid is
  configurable, and a column per band needs a migration to change one.

## Open Questions

- **Whether `available_at` and `finality_status` belong on the swap row or in a
  join.** They live on [[REQ-WP-014]]'s chain records today, and duplicating them
  would create two answers to one question.
