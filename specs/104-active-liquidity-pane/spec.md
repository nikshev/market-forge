---
traces: [REQ-WP-063]
status: draft
---

# Feature Specification: The active liquidity pane draws the rows that can carry it

**Feature Branch**: `wp-063-active-liquidity-pane`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-063 — PRD §27.3's ninth lower pane.

## Context

Eight of §27.3's nine panes existed. The ninth was absent through three
requirements because nothing produced the number; REQ-WP-060 put
`active_liquidity` on a canonical row and REQ-WP-062 gave that table a producer.

The pane reads a different field of the state than the depth curve does, so it
takes a different rule about which reconstruction grades it may read.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A partially reconstructed pool still shows its liquidity (Priority: P1)

**Acceptance**: a `partial_ticks` row is read. Inheriting the traversal's rule
would empty the pane, since every row REQ-WP-062 writes today is that grade.

### User Story 2 - An undated or contradicted row is not drawn (Priority: P1)

**Acceptance**: `gapped` and `diverged` rows yield no value, each named.

### User Story 3 - A pane on a historical chart sees no future (Priority: P1)

**Acceptance**: a state computed after the instant asked for is never read,
through the query and through the feature.

### Edge Cases

- No usable row: no value, not zero. Zero is the reading for a pool whose
  liquidity left.
- An unusable newer row must not hide a usable older one.
- A row exactly at the instant is visible.
- `uint128` into `float64` loses digits; here that is below a pixel.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `dex_active_liquidity` registered with §19's sixteen fields.
- **FR-002**: `USABLE_FOR_ACTIVE_LIQUIDITY` is `anchored`, `replayed`,
  `partial_ticks` — stated, and asserted to differ from `DEPTH_CAPABLE`.
- **FR-003**: The newest usable reading at or before `at_ns` wins.
- **FR-004**: No usable reading yields `None`.
- **FR-005**: `read_states` filters by chain and pool and honours `as_of_ns`.
- **FR-006**: The stored `uint128` comes back as `int`.
- **FR-007**: `panes.ts` offers nine panes.

### Key Entities

- **LiquidityReading** — the three fields the feature depends on.
- **PoolStateReading** — a stored state as a reader gets it back.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `partial_ticks` row yields the measured pool's liquidity.
- **SC-002**: `gapped` and `diverged` yield nothing, and an unusable newer row
  does not mask a usable older one.
- **SC-003**: The float conversion's relative error is under 1e-15.
- **SC-004**: Mutating the grade set, the instant comparison, the newest-wins
  rule or the absent case is caught by a test.

## Assumptions

- The pane draws a pool-internal `L`; the cross-pool form is §18A.4's
  volume-to-active-liquidity ratio and needs a volume this does not have.

## Open Questions

- None.
