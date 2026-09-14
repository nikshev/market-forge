---
traces: [REQ-WP-071]
status: draft
---

# Feature Specification: CUSTOM_ACCOUNTING pools are quoted, never curved

**Feature Branch**: `wp-071-v4-quoting`

**Created**: 2026-09-14

**Status**: Draft

**Input**: REQ-WP-071 — PRD §18.8.1's last unbuilt rule: "do not assume the
standard curve; prefer executable quoting/simulation adapter."

## Context

[[REQ-WP-047]] classifies a v4 pool from its hook address and refuses to answer
for its fee. Nothing prices a `CUSTOM_ACCOUNTING` pool, so today they have no
price at all.

Measured at Ethereum mainnet block 25975796 on the four such pools in
`tests/fixtures/uniswap_v4/initialize.jsonl`, through a quoter and a state
reader each verified by calling `poolManager()` on it:

- Three of the four hold **zero** liquidity in the manager. A tick-map
  reconstruction reports zero depth for them.
- Two of those three absorb a whole ETH. The liquidity is in the hook.
- The fourth holds real liquidity, so the class does not say which case it is.
- Two pools quote ETH→token and then refuse to buy back the exact amount they
  just offered — one with `NotEnoughLiquidity`, one with
  `PriceLimitAlreadyExceeded`, whose two arguments are both the pool's own
  `slot0` price of `MAX_SQRT_PRICE - 1`.

So: zero liquidity is a true reading of the manager and a false answer about the
pool; a refusal is an answer; and on two of these pools a mid price does not
exist.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The curve refuses these pools (Priority: P1)

**Acceptance**: asking the concentrated-liquidity path for a `CUSTOM_ACCOUNTING`
pool raises. It never returns a depth figure, and never returns zero.

### User Story 2 - A quote is executable, sized and dated (Priority: P1)

**Acceptance**: a quote carries the pool, the direction, the exact input size and
the block. Two quotes at different sizes are different answers, not one price.

### User Story 3 - A refusal is a named outcome (Priority: P1)

**Acceptance**: a contract-level refusal raises, carrying the pool id the
contract named and the decoded reason. It is never zero, never a stale quote,
and never a quote at a size nobody asked for.

### User Story 4 - One side is not a market (Priority: P1)

**Acceptance**: a mid is computed only from a quote in each direction. Where
either side refused, asking for a mid raises.

### User Story 5 - The quoter must name the manager (Priority: P2)

**Acceptance**: a quoter whose `poolManager()` is not the manager the pool was
routed under is refused before any quote is attempted.

### User Story 6 - Replay is the same code (Priority: P1)

**Acceptance**: the adapter runs in CI against the captured fixture — including
the reverting pool and both refusal reasons — with no network access, through
the same call path the live source uses.

### Edge Cases

- A refusal at one size says nothing about another size: the adapter never
  retries downward to find a size that works.
- An endpoint that declines is not a pool that refuses: the two raise different
  exceptions, and only the second is a fact about the pool.
- An unrecognised revert selector is still a refusal, recorded verbatim — an
  unknown reason is not a missing one.
- A quoter reached at a block later than the one asked for is not that quote.
- The other three reconstruction classes are untouched.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A reconstruction gate raises for `CUSTOM_ACCOUNTING` (and for
  `UNKNOWN`), and passes the other three classes through unchanged.
- **FR-002**: A quote request names pool id, direction and exact input amount.
- **FR-003**: A quote result carries the request, the block, the output amount
  and the gas estimate.
- **FR-004**: A contract refusal raises a distinct exception carrying the pool
  id, the decoded reason and the raw payload.
- **FR-005**: Refusal reasons are decoded from selectors computed from their
  signatures, never from copied constants.
- **FR-006**: An unrecognised selector decodes to an explicit unknown reason,
  never to a recognised one and never to success.
- **FR-007**: A transport failure raises a different exception from a refusal.
- **FR-008**: A mid requires a quote in each direction at the same block, and
  raises where either refused.
- **FR-009**: A quote source is accepted only after its `poolManager()` matches
  the routing manager.
- **FR-010**: The live source and the replay source satisfy one protocol, and
  the adapter holds no branch on which it has.
- **FR-011**: A replay source asked for a request it does not hold raises rather
  than interpolating or returning the nearest one.

### Key Entities

- **QuoteRequest**: pool id, direction, exact input amount.
- **Quote**: the request, block, amount out, gas estimate.
- **Refusal**: pool id, reason, raw revert payload.
- **ChainDataProvider**: the existing chain-access protocol. It is the seam:
  live and replay differ only in which provider supplies the bytes, so the
  encoder and the decoder are one implementation, exercised both ways.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four captured pools are priced or refused exactly as the chain
  answered at block 25975796, replayed offline.
- **SC-002**: Both distinct refusal reasons in the fixture are decoded by name,
  and the pool id inside `NotEnoughLiquidity` matches the pool asked about.
- **SC-003**: The two one-sided pools yield no mid, and the attempt raises.
- **SC-004**: The class gate raises for every `CUSTOM_ACCOUNTING` pool in the
  fixture, so no path that goes through it reaches the tick kernel. One test
  deliberately goes round the gate and pins what the kernel answers there —
  `reachable=False, amount0=0` — so the hazard is asserted rather than assumed
  away.
- **SC-005**: The suite runs with no network access.

## Assumptions

- Exact-input single-hop quoting is the scope. Exact-output and multi-hop are
  not required by §18.8.1 and are out of scope here.
- Hook data is empty for these quotes. A hook demanding non-empty data would
  refuse, and that refusal is a recorded outcome like any other.
- The fixture is the acceptance surface; refreshing it is a deliberate, manual
  capture, as with every other chain fixture in this repository.
