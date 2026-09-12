---
traces: [REQ-WP-046]
status: draft
---

# Feature Specification: Curve, quoted from its own invariant

**Feature Branch**: `wp-046-curve`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-046, first half — classification and the Stableswap-NG quote.
Cryptoswap follows.

## Context

PRD §18.9 rules out the shortcut in its opening line — *"Curve must be modeled
as an invariant/quote-based AMM family rather than as a tick-based AMM"* — and
§18.9.1 repeats it for depth: *"Do not derive a fake tick map."*

**Six shapes, one venue, and the pool does not announce which.** What a pool does
do is answer some functions and revert on others, so classification is a
capability probe against the chain. Two natural-looking discriminators were
tried and measured away: no metapool answers `base_pool()`, and the original
3pool answers `get_dy_underlying` despite not being one. What actually makes a
metapool is that one of its coins is another pool's LP token — a fact about the
registry, not the pool.

**Three things in a Stableswap-NG quote are easy to get plausibly wrong.** The
fee denominator is 1e10, not the 1e6 every other venue in this project uses. The
effective fee scales with how far off peg the pool sits, so a cached fee is
wrong exactly where it matters. And balances are not what the invariant sees:
each coin carries a stored rate folding in its decimals and its accrual.

Each produces a positive, ordered, believable number. This is the fourth
appearance of that shape in this phase.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The quote is the pool's own (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a live pool's state at a pinned block, **When** a quote is computed, **Then** it equals the pool's own `get_dy` exactly.
2. **Given** a three-coin pool, **When** every ordered index pair is quoted, **Then** all agree exactly.
3. **Given** sizes spanning three decades, **When** each is quoted, **Then** all agree exactly.

---

### User Story 2 - The state is the whole state (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a pool whose fee multiplier is switched on, **When** the effective fee is computed, **Then** it differs from the base fee.
2. **Given** a pool holding an accruing token, **When** its normalised balances are computed, **Then** they differ from its raw balances.
3. **Given** a rate list shorter than the balance list, **When** a state is built, **Then** it is refused.

---

### User Story 3 - Every shape is told apart (Priority: P1)

**Acceptance Scenarios**:

1. **Given** one live instance of each shape, **When** classified, **Then** each gets its own family.
2. **Given** a contract the registry does not know, **When** classified, **Then** it is unknown — not "a pool that is not a metapool".
3. **Given** a metapool running any curve, **When** classified, **Then** it is a metapool.

---

### User Story 4 - Depth is simulated (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a grid of notionals, **When** each is quoted, **Then** slippage rises monotonically with size.
2. **Given** a basis-point target, **When** solved for, **Then** the smallest notional reaching it is returned.
3. **Given** a target the search bound cannot reach, **When** solved for, **Then** it says so rather than returning the largest tried.

### Edge Cases

- **A pool whose invariant will not settle.** The contract raises and lets LPs withdraw; it does not quote.
- **A coin exchanged for itself, or an index outside the pool.** Refused, not clamped.
- **An empty pool.** Invariant zero, which the contract returns rather than dividing by nothing.
- **A contract with a payable fallback.** Accepts every selector and returns nothing, so a probe catching only reverts would report it implements all of Curve.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A quote MUST equal the pool's own `get_dy` exactly.
- **FR-002**: Indices MUST be handled by index, and a pool of more than two coins MUST be exercised.
- **FR-003**: The fee MUST be the dynamic fee, evaluated at the midpoint of each coin's balance before and after.
- **FR-004**: The fee denominator MUST be 1e10.
- **FR-005**: The invariant MUST see rate-normalised balances, never raw ones.
- **FR-006**: A non-converging invariant MUST refuse.
- **FR-007**: Family MUST come from observed capabilities plus the registry, never from a name.
- **FR-008**: "Not a Curve pool" MUST be distinguishable from "a Curve pool that is not a metapool".
- **FR-009**: Depth MUST be built by quote simulation and by inverse solve, never from a tick map.
- **FR-010**: An unreachable depth target MUST be reported as unreachable.
- **FR-011**: Depth arithmetic MUST be exact, not floating point.
- **FR-012**: Fixtures MUST be chain reads at one pinned block, agreed by two independent endpoints.

### Key Entities

- **Capabilities**: what a contract answered, at a block, plus what the registry says.
- **Pool state**: balances, stored rates, amplification, base fee, fee multiplier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sixty quotes across four live pools match the chain exactly.
- **SC-002**: All six ordered index pairs of a three-coin pool are covered.
- **SC-003**: Nine live contracts classify correctly, one of them not a pool.
- **SC-004**: The effective fee is shown to differ from the base fee on a real pool.
- **SC-005**: Normalised balances are shown to differ from raw ones on a real pool.
- **SC-006**: A basis-point target resolves to the smallest notional reaching it.
- **SC-007**: No test opens a socket or an RPC.

## Assumptions

- **Slippage is measured against a small-probe quote, and the probe is the
  caller's.** "Small" is a fact about a coin's decimals, which this module does
  not know: a probe of 1e18 is dust in an eighteen-decimal pool and a large
  trade in a six-decimal one. The reference therefore includes the base fee,
  which makes the figure a measure of *marginal impact* rather than of total
  cost — a different and equally useful number, named so nobody confuses them.
- **Bisection is valid because the curve is monotone in notional**, which is a
  property of the invariant rather than an assumption about the data.
- **Cryptoswap is the second half** of [[REQ-WP-046]], and metapool *quoting* is
  deferred beyond it: a metapool quote is two quotes composed, and composing
  them belongs on top of a base-pool quote that is already verified.

## Open Questions

- **Whether `CRYPTOSWAP_NG` can be separated from `CRYPTOSWAP` on a live pool.**
  Nothing observable does it today, so the enumeration deliberately omits the
  distinction rather than guessing at it.
