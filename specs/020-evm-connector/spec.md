---
traces: [REQ-WP-014, REQ-BIAS-006]
status: draft
---

# Feature Specification: EVM connector

**Feature Branch**: `wp-014-evm-connector`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-014 — logs; finality; reorg; ABI decoder; RPC health.
REQ-BIAS-006 — no using later corrected or reconstructed DEX state as if known
earlier unless audit semantics explicitly allow it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Never see a log before it was available (Priority: P1)

Every chain record carries four distinct times, and a consumer at time `t` sees
only what was available at `t`.

**Why this priority**: PRD §18.19 gives the example and the rule in one
sentence: "A historical backtest at 12:00:01.500 must not see that swap even
though `block_time` is earlier." On-chain data has a different availability
model from a websocket, and treating `block_time` as availability is the
mistake the whole section exists to prevent.

**Independent Test**: A log whose block time precedes an instant but whose
`available_at` follows it, and an assertion that it is not returned.

**Acceptance Scenarios**:

1. **Given** a log with `block_time` before `t` and `available_at` after it, **When** records are read as of `t`, **Then** it is absent.
2. **Given** the same log once `available_at` has passed, **When** records are read, **Then** it is present.
3. **Given** a research read requiring `SAFE`, **When** records are read, **Then** only records that reached `safe_at` by `t` are returned.
4. **Given** any record, **When** it is built, **Then** `available_at` is at or after `observed_at`, which is at or after the block time.

---

### User Story 2 - Handle a reorg without rewriting history (Priority: P1)

A block that is reorganised out produces an invalidation record. The original
record is untouched.

**Why this priority**: PRD §18.4 rule 5 — "A reorg cannot silently mutate an
existing signal snapshot; emit an invalidation/correction event instead" — and
PRD §41 rule 6, which is the same rule seen from the research side.

**Acceptance Scenarios**:

1. **Given** a record from a reorganised block, **When** the reorg is processed, **Then** an invalidation naming the block is emitted.
2. **Given** the same record, **When** it is read afterwards, **Then** its fields are unchanged and it carries `orphaned_at`.
3. **Given** a reorg, **When** records are read as of an instant before it, **Then** the original record is still returned — it was genuinely what was known then.
4. **Given** a finalized record, **When** a reorg claims to remove it, **Then** the claim is refused.

---

### User Story 3 - Advance finality deliberately (Priority: P1)

A record moves through `SEEN`, `HEAD_CONFIRMED`, `SAFE` and `FINALIZED` under a
configurable, chain-specific policy.

**Why this priority**: PRD §18.4. Rule 1 permits low-latency use of unconfirmed
data "with an explicit quality penalty"; rule 2 defaults research to `SAFE` or
stronger. Both need the status to be a first-class field rather than an
assumption.

**Acceptance Scenarios**:

1. **Given** a confirmation depth policy, **When** blocks accumulate, **Then** a record's status advances at the configured depths.
2. **Given** a status, **When** it is read, **Then** the confirmation count is available beside it.
3. **Given** a record that has reached `SAFE`, **When** more blocks arrive, **Then** it never regresses.

---

### User Story 4 - Decode deterministically, and fail closed (Priority: P1)

Decoder selection is versioned. An unexpected implementation stops semantic
decoding while raw logs keep flowing.

**Why this priority**: PRD §18.6 — "If an implementation changes unexpectedly,
ingestion must fail closed for semantic state reconstruction while continuing
to retain raw logs." A decoder that guessed would produce plausible events from
a contract it does not understand.

**Acceptance Scenarios**:

1. **Given** a registry entry and a matching log, **When** decoding runs, **Then** the registered decoder is selected.
2. **Given** a log whose ABI hash does not match the registry, **When** decoding runs, **Then** it fails closed and the raw log is still retained.
3. **Given** two decoder versions for one protocol, **When** a log falls in a deployment range, **Then** the version for that range is chosen.
4. **Given** no matching decoder, **When** decoding runs, **Then** the raw log is retained and no event is produced.

---

### User Story 5 - Know which provider to trust (Priority: P2)

Providers are scored on latency, errors and gaps, and a failing one is cooled
down.

**Why this priority**: PRD §18.17 — "RPC is infrastructure, not a source of
unquestioned truth."

**Acceptance Scenarios**:

1. **Given** observed calls, **When** health is read, **Then** it reports latency, error rate and gap rate.
2. **Given** a provider in an error storm, **When** routing chooses, **Then** that provider is in cooldown.
3. **Given** two providers disagreeing on a block hash, **When** the check runs, **Then** the disagreement is reported, not resolved silently.
4. **Given** no healthy provider, **When** routing chooses, **Then** it refuses rather than returning an unhealthy one.

---

### Edge Cases

- What happens when a log arrives for a block already seen with a different hash? That is a reorg, handled by US2, not an update to the existing record.
- What happens when `available_at` precedes the block time? The record is refused: a collector cannot have seen something before it happened.
- What happens when a reorg removes a block that was never seen? It is recorded and ignored — the invalidation names a block nothing depended on.
- What happens when a provider returns a block with no parent hash? It is refused: the chain link is what makes reorg detection possible.
- What happens when every provider is in cooldown? Routing refuses. Returning a provider known to be failing would produce data that looks like every other record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A chain record MUST carry block time, `observed_at`, `available_at` and `safe_at`.
- **FR-002**: A read as of `t` MUST return only records whose `available_at` is at or before `t`.
- **FR-003**: A read requiring a finality status MUST return only records that reached it by `t`.
- **FR-004**: A record whose `available_at` precedes its block time MUST be refused.
- **FR-005**: A reorg MUST emit an invalidation record and MUST NOT modify the original.
- **FR-006**: An orphaned record MUST retain its original fields and gain `orphaned_at`.
- **FR-007**: A reorg claiming to remove a finalized block MUST be refused.
- **FR-008**: Finality MUST advance through `SEEN`, `HEAD_CONFIRMED`, `SAFE`, `FINALIZED` at configurable depths, and MUST never regress.
- **FR-009**: Decoder selection MUST be by protocol, version and deployment range.
- **FR-010**: A mismatched ABI hash MUST fail closed for decoding while the raw log is retained.
- **FR-011**: An unmatched log MUST produce no event and MUST retain the raw record.
- **FR-012**: Provider health MUST report latency, error rate and gap rate.
- **FR-013**: A provider in an error storm MUST be placed in cooldown, and routing MUST skip it.
- **FR-014**: A cross-provider disagreement MUST be reported, never silently resolved.
- **FR-015**: Routing with no healthy provider MUST refuse.
- **FR-016**: No module may consult a system clock or perform network I/O; the provider is supplied by the caller.
- **FR-017**: A record MUST be immutable once created.

### Key Entities

- **Raw chain record**: PRD §18.3's envelope, immutable.
- **Finality status**: where a record sits between seen and irreversible.
- **Decoder registry entry**: which decoder handles which contract over which blocks.
- **Provider health**: what a provider has been doing lately.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A record whose `available_at` is after `t` is absent from a read at `t`.
- **SC-002**: A `SAFE`-only read excludes records that had not reached it.
- **SC-003**: A reorg produces an invalidation and leaves the original unchanged.
- **SC-004**: A reorg of a finalized block is refused.
- **SC-005**: Finality advances at the configured depths and never regresses.
- **SC-006**: A mismatched ABI hash produces no event and retains the raw log.
- **SC-007**: Deployment ranges select between decoder versions.
- **SC-008**: An unhealthy provider is skipped, and no healthy provider refuses.
- **SC-009**: A cross-provider disagreement is reported.
- **SC-010**: No module references a clock or an HTTP client.

## Assumptions

- **No network.** The `ChainDataProvider` protocol is defined and no implementation ships; tests use scripted fakes. This is the same boundary [[ADR-012]] drew for the order book's transport and [[ADR-018]] for the alerter's.
- **No protocol adapters.** PRD §18.7 to §18.11 — Uniswap v3 and v4, Curve, Aerodrome, Hyperliquid — are REQ-WP-015 and beyond. This supplies the registry they plug into.
- **§18.5's discovery registry is not built.** Pools are supplied, not discovered.
- **§18.20's data-quality state machine is not built**, beyond the finality status this feature needs.
- **No storage.** Records are in memory.
