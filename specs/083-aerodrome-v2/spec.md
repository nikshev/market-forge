---
traces: [REQ-WP-045]
status: draft
---

# Feature Specification: Aerodrome v2, priced by its own invariant

**Feature Branch**: `wp-045-aerodrome`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-045, first half — the v2 curves. Slipstream follows.

## Context

PRD §18.10 states the rule outright: *depth is calculated from the correct pool
invariant, not from CL ticks*. Aerodrome v2 has two invariants — constant
product for volatile pools, and the Solidly `k = xy(x² + y²)` for stable ones —
and the pool itself says which it is.

**Pricing a stable pool as constant product gives a plausible wrong number.**
The figure stays positive, ordered and believable; every depth curve above it is
wrong by an amount nobody can reconstruct. That is the third appearance of this
failure shape in this phase of work, after a venue's contract sizes and a
venue's taker side.

**The contract is the oracle, not a recording.** An Aerodrome pool exposes
`getAmountOut(amountIn, tokenIn)` — its own answer to exactly what this module
computes. §18.25 asks for agreement "within tolerance"; because every
intermediate in `Pool.sol` is `uint256`, a faithful port can be asked for
equality instead.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The quote is the pool's own (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a real pool at a pinned block, **When** a quote is computed, **Then** it equals the contract's `getAmountOut` exactly.
2. **Given** four trade sizes across four decades, **When** each is quoted, **Then** all four agree exactly.
3. **Given** either direction, **When** quoted, **Then** the two differ.

---

### User Story 2 - Two curves stay two (Priority: P1)

**Acceptance Scenarios**:

1. **Given** one pool's reserves, **When** priced under both invariants, **Then** the answers differ.
2. **Given** a volatile pool, **When** its invariant is read, **Then** it is the product of the reserves.
3. **Given** a pool whose curve is unknown, **When** it is quoted, **Then** it is refused.

---

### User Story 3 - The iteration is honest (Priority: P1)

**Acceptance Scenarios**:

1. **Given** reserves where Newton's step rounds to zero, **When** quoted, **Then** the search terminates on the integer lattice at the right answer.
2. **Given** reserves where it cannot settle in the contract's 255 steps, **When** quoted, **Then** it refuses rather than returning its last estimate.

### Edge Cases

- **A swap of nothing.** Refused; a quote of zero reads as "no liquidity here".
- **A pool with an empty side.** Refused for the same reason.
- **A fee of zero.** A valid pool configuration and a different number, not an error.
- **Tokens with different decimals.** Normalised to 1e18 before the invariant, as the contract does — this is where a port silently drifts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A quote MUST equal the pool's own `getAmountOut` exactly.
- **FR-002**: The curve MUST come from the pool's `stable()`, never from names or tokens.
- **FR-003**: The two invariants MUST be shown to differ on identical reserves.
- **FR-004**: The fee MUST be taken from the input before the invariant.
- **FR-005**: Direction MUST change the quote.
- **FR-006**: A non-converging search MUST refuse.
- **FR-007**: A zero amount or an empty side MUST be refused.
- **FR-008**: Fixtures MUST be chain reads at one pinned block, agreed by two independent endpoints.

### Key Entities

- **Pool shape**: which curve, what decimals, what fee.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Eight quotes across two real pools match the chain exactly.
- **SC-002**: The same reserves priced both ways give different answers.
- **SC-003**: Fee-before and fee-after give different answers, and the code does fee-before.
- **SC-004**: A constructed non-converging pool raises.
- **SC-005**: No test opens a socket or an RPC.

## Assumptions

- **v2 first, Slipstream second.** The v2 curves carry the whole substance of
  [[REQ-WP-045]]; Slipstream reuses [[REQ-WP-015]]'s existing kernel and is the
  smaller half. The hard half is done first so the requirement's core is proven
  before the easy half is dressed up.
- **The nine other §18.25 tests** — reorg rollback, checkpoint/replay
  equivalence, gap failure and the rest — are the adapter's, not this module's.
  This is the quote maths; the adapter that wraps it is where event ordering and
  reorgs live.

## Open Questions

- **Whether the fixture should be refreshed periodically.** A pinned block is
  reproducible forever and describes a pool that has since moved. A refresh
  would test against a current state and lose the reproducibility; nothing here
  needs it yet.
