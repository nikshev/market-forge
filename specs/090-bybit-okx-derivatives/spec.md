---
traces: [REQ-WP-049]
status: draft
---

# Feature Specification: Bybit and OKX report funding and open interest comparably

**Feature Branch**: `wp-049-bybit-derivatives`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-049 — the derivatives half of Phase 5's two connectors.

## Context

Phase 5 needs funding dispersion, and there is no cross-venue funding series to
disperse: Bybit and OKX land public market data and no derivatives state.

The work is not that the data exists. It is that **the two venues disagree about
units and about names in ways that produce confident wrong findings**, measured
on 2026-09-12:

- **Open interest is contracts on OKX and base units on Bybit.** Read naively,
  OKX appears to hold 51.5 times Bybit's open interest on BTC; read correctly it
  holds 0.52 times. The error is exactly the contract value — a hundredfold on
  BTC, tenfold on ETH — so it moves with the instrument.
- **`OKX.fundingTime` is `Bybit.nextFundingTime`.** The same instant under
  opposite names, and OKX's own `nextFundingTime` is the settlement after.
  Matching field names puts one venue eight hours out, and a dispersion computed
  across that boundary compares a settled rate against a forthcoming one.
- **One call against four.** Bybit returns everything from one ticker; OKX needs
  funding, open interest, mark and index, with four timestamps.
- **OKX's `premium` is not the basis.** It looks like one; measured, the two are
  0.14 basis points apart, because the premium is averaged over a funding window.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Both venues produce the same state (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a recorded Bybit ticker, **When** normalized, **Then** it produces the shared derivatives state.
2. **Given** four recorded OKX responses, **When** assembled, **Then** they produce the same shape.
3. **Given** both, **When** their settlement instants are compared, **Then** they agree to the nanosecond.

---

### User Story 2 - The units are the same units (Priority: P1)

**Acceptance Scenarios**:

1. **Given** OKX's contract count, **When** converted, **Then** it matches the venue's own base figure.
2. **Given** a contract value that disagrees with the venue's, **When** used, **Then** it is refused.
3. **Given** two instruments, **When** their contract values are compared, **Then** they differ.

---

### User Story 3 - Four readings are not a snapshot (Priority: P2)

**Acceptance Scenarios**:

1. **Given** an assembled OKX state, **When** inspected, **Then** it carries how far apart its readings were.
2. **Given** readings further apart than the bound, **When** assembled, **Then** it is refused.
3. **Given** readings for two different instruments, **When** assembled, **Then** it is refused.

### Edge Cases

- **A venue publishing no funding.** Absent, not zero.
- **A timestamp in milliseconds.** Left unconverted it is a plausible instant, in 1970.
- **A missing index price.** No basis, rather than a basis against nothing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Both venues MUST normalize into the shared derivatives state.
- **FR-002**: The settlement instant MUST be the same field for both, and shown to agree.
- **FR-003**: Open interest MUST be base units for both, and the contract value MUST come from the venue.
- **FR-004**: A contract value disagreeing with the venue's own base figure MUST be refused.
- **FR-005**: An OKX state MUST carry its reading spread and refuse one beyond a caller-supplied bound.
- **FR-006**: The bound MUST have no default.
- **FR-007**: The state MUST be stamped with its oldest reading.
- **FR-008**: Readings for different instruments MUST be refused.
- **FR-009**: The basis MUST be computed the same way on both venues, and the venue's premium MUST NOT be used.
- **FR-010**: Absent fields MUST stay absent.
- **FR-011**: Fixtures MUST be one capture pass covering both venues.

### Key Entities

- **Assembled derivatives**: an OKX state plus the span of the readings behind it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both venues' settlement instants agree exactly, on every recorded pair.
- **SC-002**: The naive open-interest reading is shown wrong by exactly the contract value.
- **SC-003**: Two instruments with different contract values are covered.
- **SC-004**: The premium and the basis are shown to differ.
- **SC-005**: No test opens a socket.

## Assumptions

- **A state is no fresher than its stalest part**, so an assembled state is
  stamped with its oldest reading. Stamping it with the newest would claim a
  freshness none of it has.
- **Funding dispersion is not here.** It is a cross-venue feature and wants its
  own requirement; this makes it possible.
- **The shared session layer is not here.** Lifecycle — reconnect, keepalive,
  rate limits — is separate work, and bundling it with units and field names
  would make both harder to review.

## Open Questions

- **Whether the reading spread belongs in the shared domain model.** It is
  meaningful for any venue assembled from several calls, and today only OKX is.
