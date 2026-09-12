---
traces: [REQ-WP-046]
status: draft
---

# Feature Specification: Cryptoswap, a cubic solved the way the contract solves it

**Feature Branch**: `wp-046-cryptoswap`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-046, second half — the Cryptoswap family. Stableswap-NG landed first.

## Context

PRD §18.9 asks for the Cryptoswap shapes as distinct from Stableswap, and
§18.9.1 forbids a derived tick map for either. Where the first half ported
Stableswap-NG's Newton search, this one faces a different kind of arithmetic:
`get_y` is a **closed-form solution of a cubic**, carried out in `int256` with
hand-rolled integer cube roots, a divider chosen from the magnitude of an
intermediate to keep coefficients inside 256 bits, and a Newton fallback for
when the discriminant is unusable.

**Which contract is running had to be established, not assumed.** The deployed
tricrypto pools report `version() == "v2.0.0"` and `tricrypto-ng`'s published
`main` declares the same string. The sibling `twocrypto-ng` deployment reports
`v3.0.0` while its repository's `main` says `v2.1.0` — so for that family the
obvious source is the wrong contract, and this specification covers tricrypto
while twocrypto stays classified and unquoted.

**One oracle is not enough here.** A quote is a chain of a dozen steps:
precisions, price scales, the cubic, then a fee interpolated by how balanced the
pool is. An end-to-end comparison says the chain is wrong without saying where.
The pool's maths library is a **separate deployed contract** whose `get_y`,
`cbrt` and `reduction_coefficient` are public views taking their own arguments —
so it can be asked about states no pool is in.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The quote is the pool's own (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a live pool at a pinned block, **When** a quote is computed, **Then** it equals the pool's own `get_dy` exactly.
2. **Given** three coins, **When** every ordered pair is quoted, **Then** all six agree.
3. **Given** three pools whose coins span several decimal scales, **When** quoted, **Then** all agree.

---

### User Story 2 - The cubic is the library's own (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a pool's scaled balances, **When** the cubic is solved, **Then** it equals the library's `get_y` exactly.
2. **Given** a cube-root input on each scaling branch, **When** rooted, **Then** it equals the library's `cbrt` exactly.
3. **Given** a state the library refuses, **When** solved, **Then** it is refused.
4. **Given** a state that sends the library to its fallback, **When** solved, **Then** the fallback's answer matches.

---

### User Story 3 - The state is the whole state (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a pool's price scale, **When** it is flattened to one, **Then** the scaled balances change.
2. **Given** a trade, **When** the fee is charged, **Then** it is charged on the balances the trade leaves behind.
3. **Given** an amplification ramp in progress, **When** a quote is asked, **Then** it is refused rather than computed from a stale invariant.

### Edge Cases

- **A coin exchanged for itself, an index outside the pool, a trade of nothing.** Refused; a negative index would otherwise wrap to a pair nobody asked about.
- **A cube root of zero.** The contract reaches zero by an EVM division by zero yielding zero; Python raises, so the case is written out.
- **A fee gamma of zero.** A configuration that switches the smoothing off, not a special case.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A quote MUST equal the pool's own `get_dy` exactly.
- **FR-002**: The cubic MUST equal the maths library's `get_y` exactly, including where it refuses and where it falls back.
- **FR-003**: The cube root MUST equal the library's `cbrt` exactly, on every scaling branch.
- **FR-004**: Divisions MUST truncate toward zero as the EVM does.
- **FR-005**: Balances MUST be scaled by precision and price scale before the cubic sees them.
- **FR-006**: The fee MUST be interpolated by balance and charged on the post-trade balances.
- **FR-007**: A ramp in progress MUST be refused, not quoted from the stored invariant.
- **FR-008**: The contract's state bands MUST be enforced.
- **FR-009**: The pool's reported version MUST match the version ported from.
- **FR-010**: Fixtures MUST be chain reads at one pinned block.

### Key Entities

- **Pool state**: balances, precisions, price scales, `A`, `gamma`, the invariant, the fee parameters, the ramp deadline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ninety quotes across three live pools match the chain exactly.
- **SC-002**: Nine solutions of the cubic on real state match the library exactly.
- **SC-003**: Seventeen cube roots and seven fee coefficients match the library exactly.
- **SC-004**: Every band has a case violating only it.
- **SC-005**: The library's refusals and its fallback are both exercised against the chain.
- **SC-006**: No test opens a socket or an RPC.

## Assumptions

- **Twocrypto is classified and not quoted.** Its deployed version has no
  matching published source, and porting the nearest one would be precisely the
  error this whole approach exists to prevent. Recorded as not delivered rather
  than approximated.
- **The stored invariant is trusted only outside a ramp.** Recomputing `D` from
  scratch is what the pool does during one, and this does not implement it —
  refusing is the honest boundary, and the refusal is testable.

## Open Questions

- **Whether the fixture should include a pool mid-ramp.** It would exercise the
  refusal against a real state rather than a constructed one; ramps are rare and
  none of the three pools was in one.
