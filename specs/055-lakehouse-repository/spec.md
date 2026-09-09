---
traces: [REQ-STORE-002]
status: draft
---

# Feature Specification: The API's reads from the canonical plane

**Feature Branch**: `store-002-lakehouse-repository`

**Created**: 2026-09-09

**Input**: REQ-STORE-002 — ADR-019's durable repository, and the tables it reads.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Serve every read the port declares (Priority: P1)

Markets, bars, channel snapshots, feature points, signals, one signal, a score.

**Why this priority**: a repository that serves six of seven reads cannot
replace the one it is meant to replace.

**Acceptance Scenarios**:

1. **Given** each read, **When** it is called on a populated repository, **Then** it answers.
2. **Given** an empty repository, **When** each read is called, **Then** it answers without raising.
3. **Given** a market nobody scored, **When** its score is read, **Then** it is absent rather than empty.

---

### One suite, both implementations (Priority: P1)

**Why this priority**: [[ADR-019]] promised the swap would change no endpoint.
Two suites would drift, and the first divergence would be a behaviour one
implementation has and the other does not, with nothing saying which is right.

**Acceptance Scenarios**:

1. **Given** the conformance suite, **When** it runs, **Then** it runs against both implementations.
2. **Given** every existing endpoint test, **When** the suite runs, **Then** each runs against both.

---

### User Story 3 - Keep the properties the models carry (Priority: P1)

**Why this priority**: the round trip is where a nested model loses something
quietly.

**Acceptance Scenarios**:

1. **Given** a channel snapshot, **When** it is read back, **Then** its quality components and forecast array are intact.
2. **Given** an instant, **When** a snapshot is read as of it, **Then** no later snapshot is returned.
3. **Given** a signal, **When** it is read back, **Then** its transitions are in the order they happened, whatever order the rows arrive in.
4. **Given** a signal, **When** it is looked up by its deep link's id, **Then** it is found.
5. **Given** two scores for one market, **When** the score is read, **Then** it is the newest and carries only its own contributions.

---

### Edge Cases

- What happens when two scores share an instant? Their contributions join on the score's own id, not on the instant.
- What happens when two transitions share a bar close time? An ordinal keeps their order; a close time is not one.
- What happens to a decimal column holding a float? Refused: the stored value has to be the text it was written as.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every read the port declares MUST be served from canonical tables.
- **FR-002**: One conformance suite MUST run against both implementations.
- **FR-003**: Every existing endpoint test MUST run against both.
- **FR-004**: A channel snapshot MUST never be later than the instant asked for.
- **FR-005**: Quality components and forecast arrays MUST survive the round trip.
- **FR-006**: A transition history MUST be restored by its recorded order.
- **FR-007**: A signal MUST be reachable by its deep link's id.
- **FR-008**: A score's contributions MUST join to that score and no other.
- **FR-009**: The newest score for a market MUST be the one returned.
- **FR-010**: An absent thing MUST be `None`, not an empty one.
- **FR-011**: An empty repository MUST answer every read without raising.
- **FR-012**: A decimal column MUST refuse anything but its exact text on read.

### Key Entities

- **Lakehouse repository**: the port's seven reads over seven tables.
- **Score id**: a score's own identity, so its contributions are its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every conformance test passes for both implementations.
- **SC-002**: Every endpoint test passes for both.
- **SC-003**: A snapshot as of one nanosecond before a later one returns the earlier.
- **SC-004**: A snapshot round-trips equal, quality and forecast included.
- **SC-005**: A shuffled transition list restores the original history.
- **SC-006**: A signal is found by `signal_id_for`.
- **SC-007**: Of two scores, the second is returned with only its own groups.
- **SC-008**: An unscored market, a missing signal and a missing snapshot are each `None`.
- **SC-009**: Every read on an empty repository returns an empty answer.
- **SC-010**: A float in a decimal column raises.

## Assumptions

- **The in-memory repository stays.** It is the fixture every test builds, and the point of a port is that both exist.
- **Writers are for tests and backfills.** A process that fills the tables from a live feed is deployment work.
- **§29.7's outcome table is separate work.** [[REQ-BT-001]] models outcomes and nothing joins them to signals yet.
