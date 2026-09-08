---
traces: [REQ-WP-015]
status: draft
---

# Feature Specification: Uniswap v3 adapter

**Feature Branch**: `wp-015-uniswap-v3`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-015 — pool math; swap decode; mint/burn; tick state; depth
simulation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert between the pool's three ways of saying "price" (Priority: P1)

A pool reports `sqrtPriceX96` and a tick. Both mean a price, and converting
between them is exact enough that a round trip returns where it started.

**Why this priority**: Every other number in this feature is derived from these
conversions. A rounding error here becomes a wrong depth curve, and a depth
curve is not obviously wrong from looking at it.

**Acceptance Scenarios**:

1. **Given** a `sqrtPriceX96`, **When** it is converted to a price, **Then** it is the square of the value divided by 2^96, in token1 per token0.
2. **Given** a tick, **When** it is converted to a price, **Then** it is `1.0001^tick`.
3. **Given** a price, **When** it is converted to a tick and back, **Then** the price is within one tick spacing of where it started.
4. **Given** token decimals, **When** a human-readable price is requested, **Then** the decimal difference is applied.

---

### User Story 2 - Rebuild pool state from events, in the chain's order (Priority: P1)

Swaps, mints and burns applied in block, transaction-index, log-index order
produce the pool's state.

**Why this priority**: PRD §18.7 states the rule and the trap in consecutive
sentences: "Do not reconstruct state by sorting only on timestamp. Canonical
event ordering is `block_number`, `transaction_index`, `log_index`." Several
events share a block timestamp, and a timestamp sort puts them in whatever
order they arrived.

**Independent Test**: A scripted event sequence whose timestamp order differs
from its canonical order, and an assertion that the reconstructed state follows
the canonical one.

**Acceptance Scenarios**:

1. **Given** events out of order, **When** state is rebuilt, **Then** they are applied in canonical order.
2. **Given** events sharing a block time, **When** state is rebuilt, **Then** transaction and log index break the tie.
3. **Given** a swap, **When** it is applied, **Then** the current tick and `sqrtPriceX96` become the swap's.
4. **Given** a mint, **When** it is applied, **Then** `liquidityNet` rises at the lower tick and falls at the upper.
5. **Given** a burn, **When** it is applied, **Then** the mint's effect is reversed exactly.
6. **Given** a mint whose range spans the current tick, **When** it is applied, **Then** active liquidity rises; when it does not span it, active liquidity is unchanged.

---

### User Story 3 - Decode the pool's events (Priority: P1)

`Swap`, `Mint` and `Burn` logs become typed events. `Collect` is decoded and
marked as LP economics, not liquidity state.

**Why this priority**: REQ-WP-015's acceptance names swap and mint/burn
decoding, and PRD §18.7 is explicit that `Collect` is "optional... for LP
economics, not for liquidity state itself" — decoding it into the tick map
would corrupt the state it is not part of.

**Acceptance Scenarios**:

1. **Given** a `Swap` log, **When** it is decoded, **Then** amounts, `sqrtPriceX96`, liquidity and tick are recovered.
2. **Given** a `Mint` or `Burn` log, **When** it is decoded, **Then** the tick range and liquidity amount are recovered.
3. **Given** a `Collect` log, **When** state is rebuilt, **Then** liquidity is unchanged.
4. **Given** a log with an unknown topic, **When** decoding runs, **Then** no event is produced and the raw record is retained.

---

### User Story 4 - Ask what it costs to move the price (Priority: P1)

Given the pool's state, the notional required to move the price by a number of
basis points, in either direction.

**Why this priority**: PRD §18.7.1 asks for "cumulative notional required for
±10/25/50/100 bps" and the local price impact curve. It is what the whole
adapter is for — everything above exists to make this number honest.

**Independent Test**: A single-range pool where the arithmetic is hand-checkable
in closed form, and then a multi-tick pool where the traversal matters.

**Acceptance Scenarios**:

1. **Given** a pool with liquidity in one range, **When** depth to a target price is computed, **Then** it matches the closed-form amount.
2. **Given** initialized ticks between spot and target, **When** depth is computed, **Then** liquidity changes at each crossing.
3. **Given** a target beyond all initialized liquidity, **When** depth is computed, **Then** it reports that the price cannot be reached rather than returning a number.
4. **Given** the same distance up and down, **When** both are computed, **Then** they may differ, and the asymmetry is reported.

---

### User Story 5 - Notice when the reconstruction has drifted (Priority: P2)

Reconstructed state is compared against a direct contract read, and a
divergence raises an incident rather than being patched.

**Why this priority**: PRD §18.7.2. "Never silently patch historical derived
rows" is the same rule [[ADR-033]] applies to reorgs — a correction that
rewrites the past makes a replay disagree with what actually ran.

**Acceptance Scenarios**:

1. **Given** matching states, **When** they are compared, **Then** no incident is raised.
2. **Given** a divergence, **When** they are compared, **Then** an incident naming the mismatched fields is raised.
3. **Given** a divergence, **When** the incident is handled, **Then** the reconstructed state is not modified in place.

---

### Edge Cases

- What happens when a swap arrives for a tick outside the initialized range? It is applied — the pool's own state is authoritative, and the tick map being incomplete is a gap in our view, not in the chain.
- What happens when a burn exceeds the liquidity at a tick? The reconstruction refuses: negative liquidity is impossible on-chain, so seeing it means the event sequence is incomplete.
- What happens when two events share block, transaction and log index? The build refuses — that triple is unique on a chain, so a duplicate means the same log was ingested twice.
- What happens when depth is asked for zero basis points? Zero notional, which is correct and not a division by zero.
- What happens when the pool has no active liquidity? Depth reports the price cannot be moved rather than dividing by zero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `sqrtPriceX96` MUST convert to price as `(value / 2^96)^2`.
- **FR-002**: A tick MUST convert to price as `1.0001^tick`, and a price to the tick at or below it.
- **FR-003**: A price-to-tick-to-price round trip MUST land within one tick of the original.
- **FR-004**: Human-readable prices MUST apply the token decimal difference.
- **FR-005**: Events MUST be applied in `block_number`, `transaction_index`, `log_index` order, never by timestamp.
- **FR-006**: A duplicate `(block, transaction index, log index)` MUST be refused.
- **FR-007**: A `Mint` MUST add `liquidityNet` at the lower tick and subtract it at the upper; a `Burn` MUST reverse it exactly.
- **FR-008**: Active liquidity MUST change only for ranges spanning the current tick.
- **FR-009**: A `Burn` exceeding the liquidity at a tick MUST be refused.
- **FR-010**: `Collect` MUST NOT change liquidity state.
- **FR-011**: An unrecognised topic MUST produce no event and retain the raw record.
- **FR-012**: Depth to a target price MUST traverse initialized ticks, changing liquidity at each crossing.
- **FR-013**: A target beyond available liquidity MUST report unreachable rather than a number.
- **FR-014**: Depth MUST be computable in both directions, and the asymmetry reported.
- **FR-015**: A divergence against a contract read MUST raise an incident naming the fields, and MUST NOT modify the reconstructed state.
- **FR-016**: No module may consult a system clock or perform network I/O.

### Key Entities

- **Pool state**: current tick, `sqrtPriceX96`, active liquidity, and the tick map.
- **Tick map**: sparse `tick -> liquidity_net`.
- **Depth quote**: what it costs to move the price a given distance, or why it cannot be moved.
- **Integrity incident**: which fields diverged, and by how much.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Price conversions match hand-computed values, and a round trip lands within one tick.
- **SC-002**: An event sequence whose timestamp order differs from its canonical order rebuilds to the canonical result.
- **SC-003**: A mint and a matching burn leave the tick map exactly as it started.
- **SC-004**: A range not spanning the current tick leaves active liquidity unchanged.
- **SC-005**: `Collect` leaves liquidity unchanged.
- **SC-006**: Single-range depth matches the closed-form amount.
- **SC-007**: Multi-tick depth differs from the single-range answer, and the difference is the crossing.
- **SC-008**: An unreachable target reports so rather than returning a number.
- **SC-009**: A divergence raises an incident and leaves the state untouched.
- **SC-010**: No module references a clock or an HTTP client.

## Assumptions

- **Log decoding takes already-split fields.** ABI decoding of packed `data` is a codec concern; the adapter takes the decoded values and the raw record, so the registry of [[REQ-WP-014]] supplies what it needs.
- **No fee accounting.** PRD §18.7's `Collect` is decoded and excluded from state; LP economics is not built.
- **Uniswap v4 (§18.8), Curve (§18.9), Aerodrome (§18.10) and Hyperliquid (§18.11) are out of scope.**
- **Depth is in pool tokens, not USD.** PRD §18.16's valuation policy is a separate concern.
- **No storage and no periodic sampler.** §18.2.3's checkpoints are unbuilt; the comparison in US5 takes a supplied contract read.
