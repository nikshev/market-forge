---
traces: [REQ-TBL-001]
status: draft
---

# Feature Specification: The `bars` canonical table

**Feature Branch**: `tbl-001-bars`

**Created**: 2026-09-09

**Input**: REQ-TBL-001 — PRD §29.4's `bars`, the first §29.B table with real data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store a bar exactly (Priority: P1)

Every field, prices as decimals.

**Why this priority**: a bar is money. A canonical table that rounded on the way
in would make every downstream figure wrong by an amount nobody could
reconstruct.

**Acceptance Scenarios**:

1. **Given** a bar, **When** it is written and read back, **Then** every field is identical.
2. **Given** a price float64 cannot hold, **When** it is read back, **Then** it is unchanged.
3. **Given** an unfinalized bar, **When** it is offered, **Then** it is refused.
4. **Given** a stored bar, **When** it is read, **Then** it is final.

---

### User Story 2 - Read a series the way the PRD orders it (Priority: P1)

**Why this priority**: PRD §29.4 states the order, and a read that returned rows
in commit order would give two readers of one snapshot different series.

**Acceptance Scenarios**:

1. **Given** bars written out of order, **When** they are read, **Then** they come back in `(venue, symbol, timeframe, open_time)`.
2. **Given** a filter, **When** a read is narrowed, **Then** only matching rows return.
3. **Given** an as-of instant, **When** a read is taken, **Then** the filter is on the bar's close and not its open.

---

### User Story 3 - Fill the table from where bars are made (Priority: P1)

**Why this priority**: PRD §29.0 forbids a storage backend in domain code, so
the producing subsystem cannot write to the table itself.

**Acceptance Scenarios**:

1. **Given** the builder's `on_final` hook, **When** a sink is attached, **Then** it is accepted directly.
2. **Given** several bars, **When** they are collected, **Then** nothing is committed until a flush.
3. **Given** an empty buffer, **When** it is flushed, **Then** nothing is committed.
4. **Given** two flushes, **When** the first snapshot is read, **Then** it is unchanged.

---

### Edge Cases

- What happens to a bar that arrives after its window was finalized? The builder already discards and counts it ([[ADR-005]]); nothing reaches the table.
- What happens when a read asks for a snapshot that does not exist? The plane refuses, as it does for any table.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every field of a `Bar` MUST round-trip exactly, prices as decimals.
- **FR-002**: An unfinalized bar MUST be refused.
- **FR-003**: A stored bar MUST read back as final, and `is_final` MUST NOT be a column.
- **FR-004**: The event-time column MUST be the bar's close.
- **FR-005**: Reads MUST return PRD §29.4's order and MUST support narrowing by venue, symbol and timeframe.
- **FR-006**: The writer MUST be usable as `BarBuilder.on_final` and MUST commit in batches.
- **FR-007**: Flushing an empty buffer MUST commit nothing.
- **FR-008**: The table MUST keep the plane's immutability and per-snapshot identity.
- **FR-009**: No storage backend MUST appear in the bar builder, and the plane MUST NOT import a domain type.

### Key Entities

- **Bars schema**: PRD §29.4's table, with money as decimals.
- **Bar sink**: the builder's hook, buffered.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A bar written and read is equal to the original.
- **SC-002**: `Decimal("0.1")` survives.
- **SC-003**: An unfinalized bar raises; a stored one reads back final; `is_final` is not in the schema.
- **SC-004**: An as-of read at one nanosecond before a bar's close returns nothing, and at its close returns it.
- **SC-005**: Three bars written in reverse come back in the PRD's order.
- **SC-006**: Each of the three filters narrows.
- **SC-007**: The sink is accepted as `on_final`; three bars buffer and commit once.
- **SC-008**: An empty flush returns nothing and commits nothing.
- **SC-009**: The first snapshot is unchanged after a second flush.
- **SC-010**: The isolation tests still pass, so neither side learned about the other.

## Assumptions

- **Only the builder's finalized output reaches the table.** [[ADR-005]] already discards a late trade and counts it.
- **A snapshot per flush is right for a backfill.** Compaction is [[REQ-STORE-001]]'s open question and not this one.
