---
traces: [REQ-WP-052]
status: draft
---

# Feature Specification: Both Hyperliquid layers plug into the machinery that exists

**Feature Branch**: `wp-052-hyperliquid-layers`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-052 — §18.11.2's HyperEVM profile and §18.25's HyperCore recovery.

## Context

PRD §18.11 splits Hyperliquid in two and [[REQ-WP-048]] delivered the market-data
half. What remains is both halves' connection to machinery this project already
has — and in each case the machinery carries a default that describes a
different venue.

**The EVM pipeline's finality defaults describe Ethereum.** Measured across
three independent endpoints:

    chain       block time   `safe` lag   `finalized` lag
    -------------------------------------------------------
    Ethereum      ~12s        33 blocks     65 blocks
    HyperEVM        1s         0 blocks      0 blocks

HyperEVM's `latest`, `safe` and `finalized` are the same block. Ethereum's
defaults make the pipeline wait 768 seconds to finality where the chain takes
one. Carried the other way, they would call a reorgable block final — the same
numbers, one direction a delay and the other wrong data.

**The session layer's policies describe three other venues.** HyperCore closes
an idle connection at 60.6 seconds with no close frame, and wants
`{"method":"ping"}` — a fourth convention after Binance's server-initiated ping,
Bybit's `{"op":"ping"}` and OKX's bare `ping`.

Because it announces nothing, a consumer holding the last book it received
cannot tell a quiet market from a dead socket.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A chain is profiled or refused (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the two profiles, **When** their times to finality are compared, **Then** they differ by orders of magnitude.
2. **Given** one confirmation count, **When** applied to both, **Then** it means different things.
3. **Given** a chain with no profile, **When** asked for one, **Then** it is refused.
4. **Given** a profile with one endpoint, **When** built, **Then** it is refused.

---

### User Story 2 - A fourth venue is a policy (Priority: P1)

**Acceptance Scenarios**:

1. **Given** HyperCore's policy, **When** it drives the shared session, **Then** it pings on schedule and infers a drop from silence.
2. **Given** the four venues, **When** their payloads are compared, **Then** three distinct strings and one server-initiated.
3. **Given** two venues with the same timeout, **When** compared, **Then** they still disagree about the payload.

---

### User Story 3 - An old book is refused (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a book past the caller's bound, **When** required fresh, **Then** it is refused.
2. **Given** no bound, **When** required fresh, **Then** it is refused.
3. **Given** a venue clock ahead of ours, **When** the age is taken, **Then** it is negative.

### Edge Cases

- **A chain id of zero.** Names no chain; refused.
- **A book exactly at the bound.** Fresh; the bound is what is allowed, not what is refused.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: HyperEVM MUST have a measured profile: identity, block time, finality depths, more than one endpoint.
- **FR-002**: A chain with no profile MUST be refused, never defaulted.
- **FR-003**: A profile MUST name more than one endpoint.
- **FR-004**: HyperCore MUST have a session policy carrying its measured timeout, payload and silence behaviour.
- **FR-005**: HyperCore MUST drive the shared session unchanged.
- **FR-006**: A book older than a caller-supplied bound MUST be refused.
- **FR-007**: The freshness bound MUST have no default.
- **FR-008**: A book age MUST be signed.
- **FR-009**: No test may open a socket.

### Key Entities

- **Chain profile**: what one chain is and how fast it settles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The two chains' times to finality differ by more than a hundredfold.
- **SC-002**: Five confirmations is final on one chain and head-confirmed on the other.
- **SC-003**: Four venues, three distinct client payloads.
- **SC-004**: A stale book is refused and a skewed clock is visible.
- **SC-005**: No test opens a socket.

## Assumptions

- **Ethereum's `safe_depth` is left as it was.** At 12 it calls a block safe
  some twenty blocks before Ethereum's own `safe` tag — a heuristic predating
  the tag. Changing it changes what every existing consumer sees.
- **A depth of one, not zero, for HyperEVM.** A record with no confirmations is
  one this collector has seen and the chain has not yet agreed to; the pipeline
  has no way to say "final on arrival" other than counting the block itself.
- **Freshness lives with the venue that needed it**, and moves when a second one
  does.

## Open Questions

- **Whether Ethereum's depths should follow the chain's own tags.** The
  measurement is recorded; the change is not made here.
