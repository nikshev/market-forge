---
traces: [REQ-WP-043]
status: draft
---

# Feature Specification: Bybit linear perpetuals as canonical events

**Feature Branch**: `wp-043-bybit-connector`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-043.

## Context

PRD §5.2 names the product — "Bybit linear perps" — and §45's Phase 5 lists the
venue. [[REQ-WP-003]] established the shape a connector takes here and
[[ADR-004]] established where its fixtures come from.

**Written after the fact, and saying so.** This specification was drafted once
the connector existed, because the validator refused an `implemented`
requirement with no spec and the validator was right: the decisions below are
real, they were simply taken while building rather than before. Recording them
after is worth doing; pretending they were foreseen is not.

The connector's job is to disappear. Past the normaliser nothing downstream may
be able to tell which venue a bar came from — that is the only thing a second
venue is worth building for.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Bybit trade is a trade (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a recorded trade, **When** it is normalised, **Then** it is the same `TradeEvent` a Binance trade becomes.
2. **Given** the venue's taker side, **When** the aggressor is read, **Then** it is taken from that field and not derived from a maker flag.
3. **Given** a side this connector does not recognise, **When** it is normalised, **Then** it is refused.

---

### User Story 2 - The book reconstructs (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a recorded snapshot and the deltas after it, **When** they are applied, **Then** the book is valid with no gap.
2. **Given** any snapshot, **When** its sides are read, **Then** the best bid is below the best ask.
3. **Given** a message type this connector does not know, **When** it is normalised, **Then** it is refused.

---

### User Story 3 - Two clocks stay two (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a trade, **When** its event time is read, **Then** it is the venue's fill timestamp and not the push time.
2. **Given** a book message, **When** its event time is read, **Then** it is the matching-engine timestamp and not the push time.
3. **Given** any event, **When** ingestion time is read, **Then** it is ours and never market information.

### Edge Cases

- **A message missing a field.** Refused, not skipped: a connector that dropped what it could not read would report a quiet market, and a quiet market is a thing somebody trades on.
- **A price float64 cannot hold.** Survives, because the venue sends strings precisely so it can.
- **A snapshot arriving mid-stream.** The venue's documented reset; the book layer already handles it.
- **The cross sequence jumping.** Expected, and not a gap — see the decision below.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A recorded trade MUST normalise to the canonical `TradeEvent`.
- **FR-002**: The aggressor side MUST come from the venue's taker field.
- **FR-003**: An unrecognised side or message type MUST be refused.
- **FR-004**: Event time MUST be the venue's own market timestamp; ingestion time MUST be separate.
- **FR-005**: Snapshot and delta MUST arrive through one entry point, because the venue sends them on one topic.
- **FR-006**: Gap detection MUST use the per-topic update id.
- **FR-007**: Every fixture MUST be recorded from the live public venue by a committed tool.
- **FR-008**: Nothing about the Binance connector MUST change.

### Key Entities

- **Public trade**: one fill, with the taker's side stated.
- **Order-book message**: a snapshot or a delta, distinguished by a field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every recorded trade normalises and its side matches the raw field.
- **SC-002**: The recorded stream reconstructs with no gap.
- **SC-003**: A snapshot's best bid is below its best ask.
- **SC-004**: The update id increments by one across the recording and the cross sequence does not.
- **SC-005**: No test opens a socket.

## Decisions taken while building

- **One function for snapshot and delta.** The venue sends both on one topic and
  distinguishes them by `type`. A caller that had to know which was coming would
  be reimplementing a dispatch the venue already did.
- **`is_buyer_maker` is derived rather than left absent.** Bybit names the
  taker, so the buyer was the maker exactly when the taker was the seller. It is
  knowable from what the venue sent, and leaving it `None` would make this venue
  look like one that does not publish the flag — which is a different fact.
- **Gap detection uses `u`.** See the requirement; the documentation's prose and
  its own field table disagree, and the recording settles it.
- **A delta's first and final update id are the same number.** Bybit sends one
  id per message rather than Binance's range. Stated in the code because a
  reader who assumed a range would look for a gap that cannot appear.

## Assumptions

- **Public market data only.** Funding and open interest arrive on other
  channels and belong with the derivatives path; private endpoints would need
  credentials this project does not hold.
- **Normalisation only.** Reconnect and ping lifecycle are a session layer, and
  Bybit's 20-second ping currently lives only in the capture tool.
