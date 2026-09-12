---
traces: [REQ-WP-048]
status: draft
---

# Feature Specification: HyperCore normalizes into the shared CLOB primitives

**Feature Branch**: `wp-048-hypercore`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-048 — HyperCore market data. HyperEVM and reconnect recovery follow.

## Context

PRD §18.11.1 puts HyperCore's output into the same primitives Binance, Bybit and
OKX produce, so it joins the order-flow and derivatives paths rather than the AMM
one. §18.25 names four things to get right, and one of them — *market symbol
normalization* — is a single line that carries most of the risk.

Measured against the live public API:

- **`allMids` keys arrive in three shapes**: 235 bare, 380 beginning `@`, 382
  beginning `#`. A key is not a symbol until something says which shape it is.
- **Delisted perps keep their index.** 56 of 234 are delisted, the first at
  index 3, and the asset-context list is positional against the same universe. A
  table built from what is still listed is right for the first three assets and
  wrong for every one after, by a drift that grows.
- **Spot pairs are sparse the other way**: 326 pairs with indices to 716, so the
  pair at position `i` is not pair `i`. One venue, two conventions, opposite
  mistakes.
- **The endpoints are not a snapshot of each other**: 55 `@N` keys matched no
  pair in metadata read seconds earlier.
- **`#N` is not established.** Its values arrive in pairs summing to one, which
  is consistent with binary markets and is not evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A key resolves or is refused (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a bare key naming a perp, **When** resolved, **Then** it is that perp.
2. **Given** an `@` key with a pair in the metadata, **When** resolved, **Then** it is that pair.
3. **Given** a `#` key, **When** resolved, **Then** it is refused, and the refusal says why.
4. **Given** an `@` key with no pair in the metadata, **When** resolved, **Then** it is refused rather than matched to a neighbour.

---

### User Story 2 - Both index conventions are honoured (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a universe containing delisted perps, **When** an index is resolved, **Then** delisted assets are counted.
2. **Given** the same universe compacted, **When** compared, **Then** it disagrees from the first delisted asset onward and agrees before it.
3. **Given** spot pairs whose indices exceed their count, **When** resolved, **Then** the pair's own index is used.

---

### User Story 3 - The book and the tape join the shared primitives (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a book payload, **When** normalized, **Then** its best bid is below its best ask.
2. **Given** the sides transposed, **When** normalized, **Then** it is refused.
3. **Given** a trade, **When** normalized, **Then** its aggressor side matches what the recording shows the venue means.
4. **Given** an asset context, **When** normalized, **Then** funding, open interest and a reference price arrive, and an absent field stays absent.

### Edge Cases

- **A quote side that is null.** An absent quote, not a quote of zero.
- **A token with an EVM decimal offset.** Its HyperCore size and its EVM amount differ by a power of ten.
- **A trade timestamp in milliseconds.** Left unconverted it is still a plausible timestamp, in 1970.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every key MUST resolve to a named instrument or be refused.
- **FR-002**: A `#` key MUST be refused while its meaning is unestablished.
- **FR-003**: Perp indices MUST count delisted assets; spot pairs MUST be found by their index field.
- **FR-004**: A key absent from the accompanying metadata MUST be refused.
- **FR-005**: A crossed book MUST be refused, not published.
- **FR-006**: The aggressor side MUST be what the venue's own recording shows.
- **FR-007**: Trade ids MUST be shown unique over the recording.
- **FR-008**: Absent derivatives fields MUST stay absent.
- **FR-009**: A token's EVM decimal offset MUST be applied.
- **FR-010**: Fixtures MUST be one capture pass, with trades and quotes on one connection.

### Key Entities

- **Symbol table**: the venue's naming as of one metadata read.
- **Namespace**: which naming scheme a key belongs to.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three key shapes are present in the fixture and handled.
- **SC-002**: The compacted universe is shown to disagree from the first delisted index.
- **SC-003**: Over 100 recorded trades, the aggressor mapping holds for more than 90% of each side.
- **SC-004**: Recorded trade ids are unique.
- **SC-005**: No test opens a socket.

## Assumptions

- **Reconnect and snapshot recovery are not here.** They belong with the socket,
  and this module touches no socket. Book freshness and trade de-duplication are
  normalization properties and are in scope.
- **`#N` stays refused** until somebody establishes what it is. The observation
  that its values pair to one is recorded as an observation.

## Open Questions

- **Whether builder-dex assets should carry their dex as a separate field**
  rather than living inside the symbol string. Nothing consumes them yet.
