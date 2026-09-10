---
traces: [REQ-INFRA-003]
status: draft
---

# Feature Specification: One event bus between producers and consumers

**Feature Branch**: `infra-003-event-bus`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-INFRA-003 — PRD §45 Phase 0's last unbuilt deliverable, "event bus abstraction".

## Context

Three producers emit events and each is told its consumer at construction:
`BarBuilder(on_final=…)`, and `BacktestRunner(on_snapshot=…, on_candidate=…)`.
[[REQ-PIPE-001]]'s replay is the one place that wires all three, and it does so
by building recorders and passing them in.

That works, and it has a specific cost: **a producer cannot be observed by
anyone it was not constructed with.** Adding a second consumer — a metric, a
log, a live publisher — means changing the producer's construction site, and
every consumer that wants the same event has to be threaded through the same
parameter.

The bus removes that. A producer publishes; whoever wants the event subscribes.

What this is not: a message broker, a queue, or anything asynchronous. PRD §45
asks for an abstraction and Principle XI requires a replay to reproduce a result
exactly — so dispatch is synchronous and ordered, and that is a requirement
rather than an implementation choice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A producer does not name its consumers (Priority: P1)

A component emits an event without knowing who, if anyone, is listening.

**Why this priority**: This is the whole abstraction. Everything else is a
property of it.

**Independent Test**: Publish an event with no subscribers, then with two, and
observe the producer's code is the same in both cases.

**Acceptance Scenarios**:

1. **Given** a bus with no subscribers, **When** an event is published, **Then** nothing happens and nothing raises.
2. **Given** two subscribers to one event type, **When** an event is published, **Then** both receive it.
3. **Given** subscribers to different event types, **When** an event is published, **Then** only the matching subscribers receive it.

---

### User Story 2 - Two identical runs deliver identical sequences (Priority: P1)

A replay produces the same events in the same order every time.

**Why this priority**: Principle XI. A bus that reordered would break
reproducibility at the foundation while looking like plumbing, and the failure
would surface far from its cause.

**Independent Test**: Record delivery order across two runs of one input and
compare.

**Acceptance Scenarios**:

1. **Given** several subscribers, **When** an event is published, **Then** they run in subscription order.
2. **Given** one input replayed twice, **When** both runs publish through a bus, **Then** the delivered sequences are equal.
3. **Given** a subscriber that raises, **When** an event is published, **Then** the failure propagates rather than being swallowed.

---

### User Story 3 - The replay path uses it (Priority: P1)

What [[REQ-PIPE-001]] records is unchanged, and the recorders reach the events
by subscribing rather than by being handed in.

**Why this priority**: An abstraction with no consumer is speculative
generality. This is what makes the deliverable closed rather than available.

**Acceptance Scenarios**:

1. **Given** the replay path, **When** it runs, **Then** the recorders receive their events through the bus.
2. **Given** the same input before and after this change, **When** a replay runs, **Then** the bars, snapshots, signals and dataset identity are identical.

### Edge Cases

- **A subscriber added while an event is being dispatched.** It must not receive the event in flight, and iterating a list being mutated must not be the way that is decided.
- **The same handler subscribed twice.** It is called twice — a bus that silently deduplicated would make a caller's double registration invisible.
- **A subclass of a subscribed event type.** Out of scope: subscription is by exact type, and inheritance-based dispatch is a separate decision nobody needs yet.
- **An event type with no `@dataclass`.** Events are values; anything else is out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A producer MUST be able to publish an event without naming any consumer.
- **FR-002**: A consumer MUST be able to subscribe to an event type and receive every event of that type.
- **FR-003**: An event with no subscriber MUST be published without error and without effect.
- **FR-004**: Subscribers MUST be called synchronously, in subscription order.
- **FR-005**: A subscriber's exception MUST propagate.
- **FR-006**: Subscribing during dispatch MUST NOT deliver the event in flight.
- **FR-007**: The same handler subscribed twice MUST be called twice.
- **FR-008**: Dispatch MUST be by exact event type.
- **FR-009**: The replay path MUST publish through the bus and its recorders MUST subscribe.
- **FR-010**: What a replay records MUST be unchanged: the same bars, snapshots, signals and dataset identity.

### Key Entities

- **Event**: a value describing something that happened — a finalized bar, a fitted channel, a candidate's latest state.
- **Bus**: the registry of subscriptions and the thing that delivers to them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Publishing to an empty bus raises nothing and changes nothing.
- **SC-002**: Two subscribers to one type both receive an event; a subscriber to another type receives none.
- **SC-003**: Delivery order equals subscription order.
- **SC-004**: Two replays of one input deliver equal event sequences.
- **SC-005**: A raising subscriber's exception reaches the publisher.
- **SC-006**: A handler subscribed twice is called twice per event.
- **SC-007**: A subscription made during dispatch receives the next event and not the current one.
- **SC-008**: The replay path's recorded output is byte-identical to what it recorded before the bus existed.

## Assumptions

- **Synchronous and ordered is a requirement, not a design choice.** Principle XI depends on it, so it is stated where a reviewer will see it rather than left to the implementation.
- **Exact-type dispatch.** Subscribing to a base class and receiving subclasses is a real feature and nobody needs it; adding it later is easier than removing it.
- **The bus does not persist, retry, or buffer.** Those belong to a transport, and [[ADR-002]]'s canonical plane is where durability lives.
- **Live mode is out of scope.** PRD §25.1's other mode is what a bus most obviously serves and it does not exist; this specification does not build it.
- **If the replay path does not read better through the bus, that is a finding.** The deliverable would then be closed by an argument rather than by code, and [[REQ-PHASE-0]] would stay open. This is written down before the work starts so the conclusion is not chosen afterwards.
