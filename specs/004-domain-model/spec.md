---
traces: [REQ-WP-002]
status: draft
---

# Feature Specification: Canonical domain model

**Feature Branch**: `004-domain-model`

**Created**: 2026-09-07

**Status**: Draft

**Input**: REQ-WP-002 — implement all canonical events as immutable/frozen Pydantic models where practical. Done when: serialization fixtures stable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Round-trip an event without losing anything (Priority: P1)

A connector normalizes a raw exchange message into a canonical event, writes it
out, and reads it back. Every field returns exactly as written — no rounding, no
drift, no silently dropped precision.

**Why this priority**: This is the requirement's only stated acceptance
criterion, and it is the foundation every later work package builds on. A model
that loses a nanosecond or a decimal place makes every downstream claim about
non-repainting untrustworthy.

**Independent Test**: Construct one instance of each canonical event, serialize,
deserialize, and compare with the original for equality. No services needed.

**Acceptance Scenarios**:

1. **Given** an event with a nanosecond timestamp above JavaScript's safe integer range, **When** it is serialized and read back, **Then** the timestamp is identical to the nanosecond.
2. **Given** a price with more significant digits than a double can hold, **When** it is serialized and read back, **Then** the value is exactly equal, not approximately.
3. **Given** any canonical event, **When** it is serialized twice, **Then** both outputs are byte-identical.

---

### User Story 2 - Reject a malformed event at construction (Priority: P1)

A connector receives a message missing a field the system depends on, or
carrying an implausible value. The model refuses to construct rather than
producing an object that looks valid and fails later.

**Why this priority**: Equal to US1. PRD §0.4 forbids conflating the six
timestamp kinds, and a model that lets `ingest_time_ns` be omitted makes that
rule uncheckable. Failing at the boundary is the difference between a bad
message and a corrupted dataset.

**Independent Test**: Attempt to construct each event with a required field
missing and with a wrong-typed field; each attempt raises.

**Acceptance Scenarios**:

1. **Given** an event payload missing `ingest_time_ns`, **When** construction is attempted, **Then** it raises and the error names the field.
2. **Given** a trade whose `aggressor_side` is not one of the permitted values, **When** construction is attempted, **Then** it raises.
3. **Given** a constructed event, **When** any field is assigned to, **Then** it raises — events are immutable once built.

---

### User Story 3 - Identify an event for deduplication (Priority: P2)

An ingestion path receives the same event twice — a websocket replay, a
backfill overlapping live data — and can tell it is the same event.

**Why this priority**: PRD §11.2 states the identity tuples, and duplicate
handling is a data-integrity requirement rather than a nicety. Lower than US1
and US2 only because it builds on them.

**Independent Test**: Two events with identical identity fields but different
arrival metadata produce the same identity; changing an identity field changes it.

**Acceptance Scenarios**:

1. **Given** two CEX trades with the same venue, symbol and trade id, **When** their identities are compared, **Then** they are equal even if `ingest_time_ns` differs.
2. **Given** two DEX logs with the same chain id, transaction hash and log index, **When** their identities are compared, **Then** they are equal.

---

### Edge Cases

- What happens when an order book delta carries a level with zero quantity? That is a level removal, not a malformed level, and must be representable.
- What happens when an optional field the PRD marks `| None` is absent? It is None, and that is distinct from being zero.
- What happens when a price is negative? Rejected for trades and book levels; permitted for funding rate and basis, which are legitimately signed.
- What happens when a JavaScript client reads a serialized event? It must not silently round the timestamp. Nanosecond values today exceed the safe integer range by more than two orders of magnitude.
- What happens when two processes serialize the same event? Byte-identical output, or fixtures cannot be compared.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a frozen model for each canonical event in PRD §10: trade, order book delta, book snapshot, derivatives state, liquidation, DEX swap, DEX liquidity change.
- **FR-002**: Every canonical event MUST embed `EventMeta` carrying every field PRD §9 lists, per ADR-003.
- **FR-003**: Events originating on a blockchain MUST additionally carry the chain fields PRD §9 names: block number, transaction index, log index and transaction hash.
- **FR-004**: Every monetary quantity MUST be an exact decimal type, per ADR-003. Dimensionless ratios MAY be floating point.
- **FR-005**: Models MUST reject construction when a required field is missing or a value is outside its permitted set, and the error MUST name the field.
- **FR-006**: Models MUST be immutable after construction; assignment MUST raise.
- **FR-007**: Serialization MUST preserve nanosecond timestamps exactly for consumers that cannot represent integers beyond 2^53 — that is, they MUST NOT be emitted as bare JSON numbers.
- **FR-008**: Serialization MUST preserve decimal values exactly and MUST NOT emit them as JSON numbers.
- **FR-009**: Serializing the same event twice MUST produce byte-identical output.
- **FR-010**: A round trip through serialization and back MUST produce an object equal to the original.
- **FR-011**: Each event MUST expose the identity PRD §11.2 defines for its kind, computed from its fields.
- **FR-012**: An order book level MUST be representable with zero quantity, denoting removal of that level.
- **FR-013**: Committed fixture files MUST exist for every event kind, and a test MUST fail when serialization output diverges from them.

### Key Entities

- **EventMeta**: the provenance and timing every event carries — where it came from, which market, when the venue said it happened, when we received it, and what the venue's own ordering identifiers were.
- **ChainMeta**: the additional position information a blockchain event has — which block, where in that block, and which transaction.
- **PriceLevel**: one side of one rung of an order book: a price and a quantity, where zero quantity means the rung is gone. Referenced by PRD §10 but never defined there.
- **Canonical event**: any of the seven kinds. Immutable, self-describing, and identifiable for deduplication.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every one of the seven event kinds round-trips through serialization with the result equal to the original.
- **SC-002**: A nanosecond timestamp taken from the current epoch survives a round trip exactly, including through a consumer that parses JSON numbers as doubles.
- **SC-003**: A decimal with more significant digits than a double can represent survives a round trip exactly.
- **SC-004**: Serializing any event twice produces identical bytes.
- **SC-005**: Committed fixtures exist for all seven kinds, and altering any model's serialization causes a fixture test to fail.
- **SC-006**: Attempting to mutate any constructed event raises.
- **SC-007**: Constructing any event without a required field raises with the field named.

## Assumptions

- Pydantic v2 is the modelling library, per PRD §7. `model_config` with `frozen=True` provides immutability, and `Decimal` is supported natively.
- Nanosecond timestamps and decimals are serialized as strings in JSON. This is what FR-007 and FR-008 require in practice; the requirement is stated as a property rather than a format so a future non-JSON encoding is not excluded.
- No persistence, no database mapping, no connector. This feature defines the shapes and proves they survive a round trip. Writing them anywhere is a later work package.
- The extremum, channel and signal models of PRD §13A.19 and §21 are out of scope. REQ-WP-002 says "canonical events", which §10 defines; those later models describe derived state rather than ingested events.
- `market_type` is a free string on `EventMeta` for now. PRD §5 names the universes but does not enumerate a closed set, and inventing one here would constrain connectors that do not exist yet.
