---
traces: [REQ-WP-060]
status: draft
---

# Feature Specification: A reconstructed pool state knows how much of itself it knows

**Feature Branch**: `wp-060-pool-state-reconstruction`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-060 — PRD §18.12.2's `reconstruction_quality` and §18.24's
`quality()`.

## Context

REQ-WP-015 already reconstructs Uniswap v3 pool state: ordered events, the sparse
tick map, duplicate and negative-liquidity refusals, §18.7.2's contract
comparison. What is missing is the field §18.12.2 ends on.

It is load-bearing because the state's two halves behave differently under a
partial replay. Active liquidity self-heals — every `Swap` reports it. The tick
map does not: it holds only the mints and burns the window saw.

Measured on Ethereum's deepest USDC/WETH pool, replaying its last 100 blocks:
active liquidity 5481181047667912297 and tick 197999, **both exactly the
contract's own**, with an empty tick map. §18.7.1's traversal over it reported
fifty basis points unreachable at zero notional. REQ-WP-059 draws that as
"exhausted at 0 bps".

§18.7.2's recovery check does not catch it: two scalars matched exactly, the
third differed by 1.4e-8 relative — noise — and it never looks at the tick map.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A partial reconstruction says so (Priority: P1)

An operator replays a recent window of a pool and asks for its depth.

**Acceptance**: the state is `PARTIAL_TICKS` and the curve is refused, with both
liquidity figures in the message. It is not a thinner curve.

### User Story 2 - The detection needs no archive node (Priority: P1)

**Acceptance**: the verdict comes from `sum(liquidity_net for tick <=
current_tick) == active_liquidity`, whose two sides come from different events.
No contract read is required to reach `PARTIAL_TICKS`.

### User Story 3 - A gap outranks a balanced map (Priority: P1)

Ingestion knows it missed a block range; the surviving events happen to balance.

**Acceptance**: the state is `GAPPED`, and the quality gate refuses a curve even
though the traversal's own check passes.

### User Story 4 - A reconciliation counts only where it means something (Priority: P2)

**Acceptance**: a contract read at the state's own block that disagrees gives
`DIVERGED`; one at another block gives neither `DIVERGED` nor `ANCHORED`.

### Edge Cases

- Liquidity minted exactly at the current tick: the range is active at its lower
  bound, so that tick counts.
- A pool with no active liquidity and no ticks: the invariant holds at zero, and
  its depth is honestly nothing.
- A map missing its lower ticks can imply *negative* liquidity; the column keeps
  the sign.
- REQ-WP-015's `NegativeLiquidity` catches some partial replays and not others —
  both cases are in the fixture.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ReconstructionQuality` has five classes, derived.
- **FR-002**: `implied_active_liquidity` sums `liquidity_net` over ticks `<=`
  the current tick.
- **FR-003**: `quality()` checks contiguity, then the invariant, then the
  reconciliation.
- **FR-004**: `Reconciliation` is evidence only when read at the state's block.
- **FR-005**: the traversal refuses a state failing the invariant.
- **FR-006**: a second gate refuses by quality class, covering the gap case.
- **FR-007**: `Provenance` refuses a backwards range.
- **FR-008**: `dex_state` carries §18.12.2's producible fields plus the replayed
  range and the implied liquidity, so the verdict is recomputable from the row.

### Key Entities

- **ReconstructionQuality**, **Provenance**, **Reconciliation**
- **LiquidityState row** — §18.12.2, minus the two fields with no producer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: the fixture's 100-block replay matches the contract on tick and
  liquidity, implies zero, and is refused.
- **SC-002**: the fixture's 400-, 800- and 2000-block replays raise
  `NegativeLiquidity`; the 100- and 200-block ones do not.
- **SC-003**: replaying in two halves reaches the same state as replaying whole.
- **SC-004**: mutating the tick boundary, the invariant, the class ordering, the
  alignment rule or either gate is caught by a test.

## Assumptions

- Equality of the two liquidity figures is treated as completeness. Cancelling
  errors are possible and not relied upon being impossible.

## Open Questions

- Nothing yet drives this from stored `dex_liquidity` rows; the reconstruction is
  invoked with events a caller supplies.
