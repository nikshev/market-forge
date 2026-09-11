---
traces: [REQ-WP-045]
status: draft
---

# Feature Specification: A Slipstream fee is an observation, not a derivation

**Feature Branch**: `wp-045-aerodrome`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-045, second half — Slipstream. The v2 curves landed first.

## Context

PRD §45's Phase 4 asks for an "Aerodrome Slipstream adapter using shared CL
kernel", and the phrase contains the hazard. Slipstream is a Uniswap v3 fork:
the tick map, the active liquidity and the depth traversal are the same
arithmetic, already built and already verified by [[REQ-WP-015]]. Sharing them
is correct.

**What must not be shared is the assumption underneath them.** Slipstream's
`Swap` event is byte-identical to Uniswap v3's — same arguments, same topic
hash. A v3 decoder pointed at a Slipstream pool reads every swap correctly, and
is wrong about exactly one thing, silently:

- **The pool key is `(token0, token1, tickSpacing)`, not `(token0, token1, fee)`.**
  The factory's own table is not injective — spacings 10, 50 and 100 all
  default to 500 pips — so neither value determines the other. In Uniswap v3
  they do, which is why a v3 decoder feels entitled to convert between them.
- **The fee is not a property of the pool.** `CLPool.fee()` forwards to the
  factory, which forwards to a swap fee module. The module in force on Base
  computes `min(baseFee + |tick − twAvgTick| · K / 1e6, feeCap)` from the pool's
  own oracle: it moves with the price, every block, with no transaction and no
  event to subscribe to.
- **It can depend on who is asking**, through a discount registered against
  `tx.origin`, and on whether a swap is the first in its block.

Measured at one pinned block across eight live pools: **seven charge something
other than their tick spacing's default**, one of them four times it.

This is the same failure shape as the two that preceded it in this phase — a
venue's contract sizes, a venue's taker side, a stable pool priced as constant
product. The number stays positive, ordered and believable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The fee is the chain's (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a live pool's module configuration and oracle at a pinned block, **When** its fee is computed, **Then** it equals what the factory charges, exactly.
2. **Given** the same pool, **When** the fee is read from the pool and from the factory, **Then** the two agree.
3. **Given** a pool whose fee nobody observed, **When** a quote is attempted, **Then** it is refused.

---

### User Story 2 - Nothing is derived (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the factory's tick-spacing defaults, **When** compared with what live pools charge, **Then** they disagree for nearly all of them.
2. **Given** that table, **When** read in the other direction, **Then** one fee maps to several spacings.
3. **Given** two pools on one pair at two spacings, **When** keyed, **Then** they are two pools.

---

### User Story 3 - Every branch of the module is the module's (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a pool at its fee cap, **When** priced, **Then** the cap applies after the dynamic term and before any discount.
2. **Given** a pool with no scaling of its own, **When** priced, **Then** the module's default scaling *and* default cap apply together.
3. **Given** an oracle too short to answer, or one that reverts, **When** priced, **Then** no dynamic term is charged.
4. **Given** the first swap of a block in a pool that opted in, **When** priced, **Then** it may pay a different fee from the rest of that block.

### Edge Cases

- **A deliberate zero fee versus an unconfigured one.** The module stores a
  sentinel because zero already means "nothing set"; conflating them charges a
  default to a pool that charges nothing.
- **A negative average tick.** Solidity truncates toward zero and Python floors.
  They differ by one tick on every negative average that does not divide
  evenly, which at a typical scaling factor is three pips on a pool that should
  have had none.
- **An average tick outside `int24`.** Unreachable from a healthy pool; the
  contract casts anyway.
- **A pool from a factory nobody has written an adapter for.** Refused. §18.10
  names a fourth shape as a placeholder precisely because the venue keeps
  adding them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A computed fee MUST equal the factory's `getSwapFee` for that pool at that block, exactly.
- **FR-002**: Pool identity MUST be `(token0, token1, tickSpacing)`.
- **FR-003**: No fee MAY be derived from tick spacing. The default table exists for comparison only.
- **FR-004**: Entering the shared CL kernel without an observed fee MUST be refused.
- **FR-005**: The cap MUST apply after the dynamic term; any discount MUST apply after the cap.
- **FR-006**: Default scaling and default cap MUST substitute together or not at all.
- **FR-007**: A short oracle and a reverting oracle MUST each charge no dynamic term.
- **FR-008**: The curve/shape MUST come from the deploying factory, and an unrecognised one MUST be refused.
- **FR-009**: Fixtures MUST be chain reads at one pinned block, agreed by two independent endpoints.

### Key Entities

- **Pool key**: the pair and the tick spacing.
- **Fee schedule**: the module's per-pool configuration at a block.
- **Oracle**: what the pool's own observations say at that block.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Eight live pools' fees are reproduced exactly.
- **SC-002**: The tick-spacing default is shown wrong for at least seven of the eight, one by a factor of two or more.
- **SC-003**: At least one pool carries a live dynamic term.
- **SC-004**: Truncating and flooring division are shown to differ.
- **SC-005**: All three live Slipstream factories are recognised.
- **SC-006**: No test opens a socket or an RPC.

## Assumptions

- **The CL arithmetic is [[REQ-WP-015]]'s and is not rebuilt here.** Tick map,
  active liquidity and depth traversal are the same as Uniswap v3's and are
  already verified. This specification covers only what a shared kernel would
  otherwise get silently wrong.
- **The venue-level fee is the undiscounted one.** A fee read without a sender
  is what the pool charges anyone not registered for a discount, which is the
  right number for a market-structure feature and the wrong one for a
  particular account's execution. The discount is therefore a parameter with no
  default rather than something inferred.

## Open Questions

- **Whether a fee should be re-read per block or per swap.** Per block is the
  natural granularity for depth features and is what the fixture pins. Per swap
  matters only for the initial-fee path, which no pool in the fixture has
  enabled.
