---
traces: [REQ-WP-062]
status: draft
---

# Feature Specification: A pool state is rebuilt from the rows the plane already holds

**Feature Branch**: `wp-062-materialize-liquidity-state`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-062 — PRD §18.7's reconstruction over §18.12.1's stored rows.

## Context

REQ-WP-053 stores swaps and liquidity changes; REQ-WP-060 rebuilds a state and
grades it. Nothing joined them, so `dex_state` had no producer — the shape
REQ-PIPE-001 closed for the other seven tables.

Two things had to be settled first. §18.7's canonical order names
`transaction_index` and neither table stored it, though `ChainMeta` has always
carried it. And a `dex_liquidity` row states the same fact twice: a signed
`liquidity_delta` and an `event_type`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The table gets rows (Priority: P1)

**Acceptance**: replaying a pool's stored rows for a block range produces one
`dex_state` row whose active liquidity and tick equal the contract's.

### User Story 2 - The row is graded honestly (Priority: P1)

**Acceptance**: a recent window yields `PARTIAL_TICKS` and is written, with the
implied and reported liquidity both on the row.

### User Story 3 - A contradictory row stops the replay (Priority: P1)

**Acceptance**: `burn` over a positive delta, or `mint` over a negative one, is
refused naming both halves.

### User Story 4 - The canonical order is expressible (Priority: P1)

**Acceptance**: both tables carry `transaction_index`, and it decides before
`log_index`.

### Edge Cases

- A `Burn` of zero is real: 4 of the fixture's 15 mint/burn logs are the poke
  that settles fees before a collect. It moves nothing and must not trip the
  burn guard, which in a partial replay is about the window.
- `modify` is v4's `ModifyLiquidity` with no `PoolEventKind`; it maps by sign.
- `collect` moves no liquidity and keeps its place in the order.
- A range with no rows: nothing written, and said.
- A window with liquidity rows and no swap: no price, so no anchor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `dex_swaps` and `dex_liquidity` carry `transaction_index`.
- **FR-002**: Rows become `PoolEvent`s and `rebuild` applies §18.7's order.
- **FR-003**: A row whose `event_type` contradicts its sign is refused.
- **FR-004**: A zero delta is applied as a change of nothing, not as a burn.
- **FR-005**: `modify` maps by the sign of its delta.
- **FR-006**: Quality is derived from the rebuilt state; the caller supplies only
  the range and its contiguity.
- **FR-007**: An empty range raises rather than writing an empty state.
- **FR-008**: A state with no price raises rather than being priced at zero.

### Key Entities

- **PoolIdentity** — what the event rows do not carry.
- **Materialized** — the state, its grade, its reference price and its row.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The rebuilt state matches the contract on liquidity and tick.
- **SC-002**: The same rows twice produce an identical row; reversed input
  produces an identical row.
- **SC-003**: Adding `transaction_index` reorders nothing that exists —
  measured over 1,392 logs in 803 blocks, 305 with multiple transactions.
- **SC-004**: Mutating the sign rules, the zero-delta branch, the order, the
  anchor check or the quality derivation is caught by a test.

## Assumptions

- Rows for one pool and range are supplied by the caller; which pools to
  materialise and how often is deployment work.

## Open Questions

- No feature computes an `active_liquidity` series from these rows, so §27.3's
  second pane stays unbuilt.
