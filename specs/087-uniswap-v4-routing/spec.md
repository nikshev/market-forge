---
traces: [REQ-WP-047]
status: draft
---

# Feature Specification: One contract, every pool, and the hook address says what is safe

**Feature Branch**: `wp-047-uniswap-v4`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-047 — Uniswap v4 routing and hook safety classification.

## Context

PRD §18.8 opens with a prohibition: v4 *"must not be implemented as 'v3 with a
different factory'"*. Three facts make that more than a stylistic note.

**One address emits everything.** Measured on Ethereum mainnet: 2960 pools
initialised in a forty-thousand-block window, every one through a single
contract. A v3-shaped ingestion keyed on `(chain_id, address)` files all of them
under one key, and the tick map that falls out is internally consistent and
describes nothing. §18.8.2 requires `(chain_id, pool_manager, pool_id)`.

**A pool id is a hash of the pool's configuration**, over five whole words with
the tick spacing sign-extended. Packed instead, every id is wrong; sign-extended
wrongly, only the pools with negative spacing are wrong — which is worse,
because most of the system keeps working.

**A hook's permissions are in its address**, not its code and not a call. That
is what makes §18.8.1's safety classification computable offline, and therefore
computable in a replay where Principle I forbids reaching for the present.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The id is the manager's own (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a real pool's key from an `Initialize` log, **When** its id is derived, **Then** it equals the id the manager emitted.
2. **Given** the same fields packed rather than encoded, **When** hashed, **Then** the result differs.
3. **Given** a negative tick spacing, **When** encoded, **Then** the sign fills the whole word.
4. **Given** a currency pair in the wrong order, **When** hashed, **Then** it is a different pool.

---

### User Story 2 - Events route by pool, not by address (Priority: P1)

**Acceptance Scenarios**:

1. **Given** many pools sharing one manager, **When** each is registered, **Then** each has a distinct route and one manager.
2. **Given** an id never initialised, **When** routed, **Then** it is refused.
3. **Given** the same id under another chain or manager, **When** routed, **Then** it is a different pool.

---

### User Story 3 - The class is the most restrictive one that applies (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a live pool of each shape, **When** classified, **Then** each gets its own class.
2. **Given** a pool that is both dynamic-fee and returns-delta, **When** classified, **Then** it is custom accounting.
3. **Given** a key the manager would reject, **When** classified, **Then** it is unknown.
4. **Given** a dynamic-fee pool, **When** its key is asked for a fee, **Then** it is refused.

### Edge Cases

- **A static-fee pool with a swap hook.** Not static: the hook may override the fee for a swap.
- **A fee of `0x800001`.** Has the sentinel's high bit and is not a dynamic fee; it is invalid.
- **A hook address with no permission bits.** The manager rejects it — it would never be called.
- **A returns-delta permission without its action permission.** Rejected, for each of the four pairs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A pool id MUST equal the manager's, on real logs.
- **FR-002**: Routing MUST use chain, manager and pool id together.
- **FR-003**: An uninitialised pool id MUST be refused.
- **FR-004**: Each of §18.8.1's five classes MUST be producible, and four of them from real pools.
- **FR-005**: The most restrictive applicable class MUST win.
- **FR-006**: A key the manager would reject MUST classify as unknown.
- **FR-007**: A fee that is not point-in-time knowable MUST be refused, not returned.
- **FR-008**: Hook permissions MUST come from the address, with no call.
- **FR-009**: The manager address MUST be discovered, and a second emitter MUST abort the capture.
- **FR-010**: Fixtures MUST be chain reads over a named block range.

### Key Entities

- **Pool key**: two currencies, a fee, a tick spacing, a hook address.
- **Routing key**: chain, manager, pool id.
- **Reconstruction class**: what depth reconstruction is permitted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sixteen real pool ids are reproduced exactly.
- **SC-002**: All four on-chain classes come from real pools.
- **SC-003**: The single-emitter measurement covers more than a thousand pools.
- **SC-004**: Seven distinct invalid keys classify as unknown.
- **SC-005**: No test opens a socket or an RPC.

## Assumptions

- **Quoting is out of scope.** §18.8.1 says a `CUSTOM_ACCOUNTING` pool wants an
  executable quoting adapter; knowing which pools need one is a different and
  prior piece of work.
- **A swap hook makes a static fee dynamic.** This is a reading of §18.8.1's
  rule rather than a quotation of it, and it follows from `OVERRIDE_FEE_FLAG`
  existing at all.

## Open Questions

- **Whether `Swap`'s own fee field should feed an effective-fee history.** §18.8
  lists "effective LP fee history" among what to track; the event carries it, and
  nothing consumes it yet.
