---
traces: [REQ-WP-021]
status: draft
---

# Feature Specification: An instrument's trading rules

**Feature Branch**: `wp-021-instrument-metadata`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-021 — PRD §45 Phase 1's last unbuilt deliverable, "basic market metadata".

## Context

The system knows a market by `venue`, `symbol` and `market_type`. It does not
know the smallest price the venue will quote, the smallest quantity it will
fill, the smallest notional it will accept, what a contract is denominated in,
or whether the instrument is trading at all.

Every one of those is needed before a result can claim a trade was realisable,
which PRD §41 rule 9 requires of any economic evaluation. A backtest filling at
an unquotable price has filled at a price that does not exist; one counting a
position below the venue minimum has counted a trade nobody could place.

This specification covers getting those numbers in, keeping them, and serving
them. **It does not cover using them** — rounding a fill, refusing a size,
skipping a halted instrument each change the execution model and each deserves
its own requirement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A venue's payload becomes instrument values (Priority: P1)

An exchange's instrument description is normalized once, at the boundary, into
values the rest of the system understands.

**Why this priority**: Everything downstream reads these. A venue's field names
and encodings must stop at the connector, as the rest of [[REQ-WP-003]] already
insists.

**Acceptance Scenarios**:

1. **Given** a venue payload describing several instruments, **When** it is normalized, **Then** one instrument value per entry is produced with the venue's names gone.
2. **Given** a payload entry missing a required rule, **When** it is normalized, **Then** it is refused naming the field and the symbol.
3. **Given** a payload whose numbers are strings, **When** it is normalized, **Then** they become decimals and no float appears in the path.
4. **Given** a spot instrument, **When** it is normalized, **Then** it has no contract size, which is different from a contract size of one.

---

### User Story 2 - The rules survive a restart (Priority: P1)

Instruments are written to the canonical plane and read back identically.

**Acceptance Scenarios**:

1. **Given** instruments written to the plane, **When** they are read back, **Then** every field equals what was written, decimals included.
2. **Given** an instrument already stored, **When** the same one is written again, **Then** it appears once.
3. **Given** instruments from two venues, **When** one venue's are read, **Then** the other's are not returned.

---

### User Story 3 - The API serves them with the market (Priority: P1)

A caller listing markets gets the trading rules with each one.

**Why this priority**: A store nothing reads is the pattern three requirements
in this repository have each recorded in turn. Serving them is what makes the
deliverable delivered rather than available.

**Acceptance Scenarios**:

1. **Given** a stored instrument, **When** markets are listed, **Then** its rules come with it.
2. **Given** a market with no instrument record, **When** markets are listed, **Then** it is returned with its rules absent rather than zeroed.
3. **Given** either repository implementation, **When** the same question is asked, **Then** the answers match.

### Edge Cases

- **A venue reporting a tick size of zero.** Refused: a zero increment is not a smaller increment, it is a missing one.
- **A negative or non-numeric rule.** Refused at the boundary rather than stored.
- **A symbol present in the payload twice.** The later entry wins, and that is stated rather than left to dict ordering.
- **A market with no instrument record.** Its rules are absent, not zero — an unknown tick size and a tick size of zero must not read alike.
- **An instrument that is halted.** Stored with its status; nothing here acts on it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A venue payload MUST be normalized into instrument values at the connector boundary.
- **FR-002**: An instrument MUST carry venue, symbol, market type, base and quote asset, tick size, step size, minimum notional, contract size and status.
- **FR-003**: A missing, zero, negative or non-numeric rule MUST be refused, naming the symbol and the field.
- **FR-004**: Quantities MUST be decimal end to end; no float may appear in the path.
- **FR-005**: A spot instrument's contract size MUST be absent rather than one.
- **FR-006**: Instruments MUST be stored on the canonical plane and read back identically.
- **FR-007**: Storing an instrument twice MUST NOT produce two records of it.
- **FR-008**: A read MUST be able to filter by venue and by symbol.
- **FR-009**: The API MUST serve an instrument's rules with the market it belongs to.
- **FR-010**: A market with no instrument record MUST have its rules absent, not zero.
- **FR-011**: Both repository implementations MUST answer alike.
- **FR-012**: No existing endpoint field MUST change.

### Key Entities

- **Instrument**: what a venue will let you trade and under what rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A payload of N instruments produces N values, and a malformed entry produces a refusal naming the symbol.
- **SC-002**: Every decimal read back equals the decimal written, exactly.
- **SC-003**: Writing one instrument twice leaves one record.
- **SC-004**: A read filtered to one venue returns none of another's.
- **SC-005**: A spot instrument's contract size is absent; a perp's is present.
- **SC-006**: Listing markets returns each one's rules, and a market without a record returns them absent.
- **SC-007**: The behavioural suite passes against both repository implementations.
- **SC-008**: Every field an endpoint returned before this change is still returned, unchanged.

## Assumptions

- **The payload arrives from the caller.** Fetching it over HTTP is out of scope, as the rest of [[REQ-WP-003]] keeps the wire behind a `Transport` protocol.
- **Binance's shape is the one normalized.** It is the only connector that exists; a second venue is a second normalizer, not a change to the value.
- **The chosen fields are a judgement about "basic".** The PRD neither confirms nor contradicts them. The derivation is written in [[REQ-WP-021]] so a disagreement has something to argue with.
- **Using the rules is a separate requirement.** Stated here so its absence reads as a boundary rather than an omission.
