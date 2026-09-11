---
traces: [REQ-WP-044]
status: draft
---

# Feature Specification: OKX swaps as canonical events, in base units

**Feature Branch**: `wp-044-okx-connector`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-044.

## Context

PRD §5.2 names the product and §45's Phase 5 lists the venue. [[REQ-WP-043]]
established the pattern a second time; this is the third venue, and it is the
one that disagrees.

**OKX quotes trade size in contracts.** `BTC-USDT-SWAP` carries `ctVal = 0.01
BTC`. Binance and Bybit both send a base-asset quantity, so two venues agreeing
taught nothing and the third is where the canonical model earns its name.

Read the same way, every volume on this instrument would be a hundred times too
large — and the failure has no symptom. The numbers stay positive, ordered and
plausible. The cross-venue comparison this whole phase exists for would read a
hundredfold difference as a finding.

**What `side` means cannot be looked up.** OKX's field table does not render
through any fetchable documentation page. It is therefore measured: replay the
interleaved recording, maintain the book, and see where each side's trades
execute.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Size is in base units (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a recorded trade and the instrument's contract value, **When** it is normalised, **Then** the quantity is contracts times contract value.
2. **Given** the same trade, **When** the notional is read, **Then** it follows the converted quantity.
3. **Given** an instrument nobody described, **When** its contract value is asked for, **Then** it is refused rather than assumed to be one.

---

### User Story 2 - The taker's side, established (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the interleaved recording, **When** each trade is compared against the book as it stood, **Then** `buy` executes at the ask and `sell` at the bid.
2. **Given** any trade, **When** the aggressor is read, **Then** it is the venue's side field.
3. **Given** a side this connector does not know, **When** it is normalised, **Then** it is refused.

---

### User Story 3 - The book states its own chain (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the recorded book messages, **When** their sequence fields are read, **Then** each `prevSeqId` is the previous `seqId` and the snapshot's is `-1`.
2. **Given** a snapshot, **When** its sides are read, **Then** the best bid is below the best ask.
3. **Given** an action this connector does not know, **When** it is normalised, **Then** it is refused.

### Edge Cases

- **A contract value of zero.** Refused: a contract worth nothing of the base asset describes nothing.
- **A trade that arrives before the delta that moved the price.** Expected in an interleaved recording, and why the side criterion is overwhelming rather than absolute.
- **A message with no data rows.** Refused.
- **A price float64 cannot hold.** Survives, because the venue sends strings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trade quantity MUST be converted from contracts to base units.
- **FR-002**: The contract value MUST come from the venue's instrument data.
- **FR-003**: An unknown or non-positive contract value MUST be refused.
- **FR-004**: The aggressor side MUST be the venue's taker side, established from recorded traffic.
- **FR-005**: An unrecognised side or action MUST be refused.
- **FR-006**: Event time MUST be the venue's own; ingestion time MUST be ours.
- **FR-007**: Book messages MUST carry the venue's own predecessor id.
- **FR-008**: Every fixture MUST be recorded from the live public venue.
- **FR-009**: Nothing about the Binance or Bybit connectors MUST change.

### Key Entities

- **Contract value**: how much of the base asset one contract is, per instrument.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A normalised quantity differs from the raw `sz` by exactly the contract value.
- **SC-002**: In the recording, `buy` trades at the ask outnumber `buy` trades at the bid by at least five to one, and likewise `sell` at the bid.
- **SC-003**: Every `prevSeqId` equals the previous `seqId`.
- **SC-004**: A snapshot's best bid is below its best ask.
- **SC-005**: No test opens a socket.

## Assumptions

- **Public market data only**, as with [[REQ-WP-043]].
- **One instrument's contract value per call.** A connector that cached a table
  would have to decide when to refresh it, and a stale contract value is the
  hundredfold error with extra steps.
