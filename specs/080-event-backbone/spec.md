---
traces: [REQ-WP-042]
status: draft
---

# Feature Specification: The event backbone, in process and over Kafka

**Feature Branch**: `wp-042-event-backbone`

**Created**: 2026-09-11

**Status**: Draft

**Input**: REQ-WP-042, following [[ADR-063]].

## Context

PRD §6.3 asks for one interface with two implementations so that a change of
transport is not a change of design. §6.4.3 says what a record carries: an
explicit schema version, a partition key, event time and ingestion time kept
apart, producer and sequence metadata, and consumers that are replay-safe where
they materialise.

[[ADR-063]] settled the rest: Kafka protocol, Redpanda on the stack, and the
Parquet written by a consumer here rather than by a connector.

**The last of §6.4.3's rules is the one with teeth.** "All consumers must be
replay-safe and idempotent where materialization occurs" is not a hint — this
repository has already paid for it. Duplicate writes on re-run were a real
defect, fixed by [[ADR-056]]'s per-series watermark, and a consumer that
materialises without that discipline puts it straight back.

**Event time and ingestion time in one field is the other trap.** PRD §9 forbids
a feature depending on ingest time as market information. A record that carried
one timestamp would make that rule unenforceable by anybody downstream, because
there would be nothing to tell them apart.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One interface, two transports (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a publisher, **When** something publishes, **Then** it does not know which implementation it holds.
2. **Given** the same test, **When** it is run against the in-process transport and the Kafka one, **Then** it passes for both.
3. **Given** a consumer, **When** it reads, **Then** the records are the ones published, with every field intact.

---

### User Story 2 - A record says what it is (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a topic name without a schema version, **When** a record is built, **Then** it is refused.
2. **Given** a record, **When** it is read, **Then** event time and ingestion time are separate fields.
3. **Given** a record with no partition key, **When** it is built, **Then** it is refused.

---

### User Story 3 - Replaying a topic writes nothing twice (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a topic of trades materialised into the canonical plane, **When** the same topic is consumed again, **Then** nothing is written the second time.
2. **Given** a topic consumed in two halves, **When** both halves are materialised, **Then** the result equals consuming it once.
3. **Given** a materialising consumer, **When** it writes, **Then** it goes through the same watermark every other entry point uses.

### Edge Cases

- **An empty poll.** No records is an answer, not an error, and not an empty commit.
- **A topic nobody has published to.** Empty, not a failure: a consumer starting before a producer is ordinary.
- **A record whose ingestion time is before its event time.** Accepted and not corrected — clocks disagree, and a transport that silently repaired timestamps would hide the disagreement from the only people who could fix it.
- **Two publishers on one topic.** Ordering is per partition key, which is what the key is for.
- **The fast gate.** No broker, and nothing in it reaches for one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: One publisher interface and one consumer interface MUST have an in-process and a Kafka-protocol implementation.
- **FR-002**: Callers MUST NOT branch on which implementation they hold.
- **FR-003**: A topic name MUST carry an explicit schema version, and one that does not MUST be refused.
- **FR-004**: A record MUST carry event time and ingestion time as separate fields.
- **FR-005**: A record MUST carry a partition key, a producer and, where a source has one, a sequence number.
- **FR-006**: A consumer that materialises into the canonical plane MUST go through [[ADR-056]]'s watermark, so replaying writes nothing twice.
- **FR-007**: The fast gate MUST need no broker; the Kafka path MUST be proven against a real one in CI.
- **FR-008**: Nothing existing MUST change.

### Key Entities

- **Record**: one event on the wire, and everything §6.4.3 says it carries.
- **Transport**: where records go; in this process, or over the Kafka protocol.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One test body passes against both transports.
- **SC-002**: A topic without a version is refused at construction.
- **SC-003**: Consuming a topic twice materialises its rows once.
- **SC-004**: `make test-fast` passes with no containers running.
- **SC-005**: The Kafka round trip passes against Redpanda in CI.

## Assumptions

- **A Kafka client joins the dependencies.** `confluent-kafka` ships binary
  wheels, so CI needs no build toolchain, and it speaks the protocol the broker
  choice is reversible through ([[ADR-063]]).
- **Payloads are JSON.** §6.4.3 requires the schema version to be explicit and a
  topic name carries it. A binary format and a registry are a different
  guarantee and a different service, named out of scope in the requirement.
- **One materialising consumer, for trades.** The seam is the deliverable; a
  topic with no producer would be a name in a config file.

## Open Questions

- **Consumer offsets and delivery semantics.** The watermark makes materialising
  idempotent, so at-least-once is enough; whether anything ever needs
  exactly-once is a question for whoever runs it.
