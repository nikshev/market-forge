---
traces: [REQ-WP-051]
status: draft
---

# Feature Specification: One stream lifecycle, three venues

**Feature Branch**: `wp-051-session-layer`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-051 — Phase 5's last item.

## Context

PRD §0 item 10 asks for a shared canonical interface and §35.6 for reconnect and
rate-limit coverage. Only Binance had a session, with its venue's rules as
constants in its own module — so there was no interface to share.

Measured by opening a connection, subscribing to nothing, and timing the close:
Binance is pinged by the venue; Bybit closes an idle connection at 60.7 seconds
**with no close frame**; OKX closes at 30.9 seconds with code 4004 and a reason.
Subscribed to a busy channel, neither closed in five and a half minutes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The venues differ, and the differences are data (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the three policies, **When** compared, **Then** they disagree about keepalive direction, payload and timeout.
2. **Given** a policy whose ping cannot outpace its own timeout, **When** built, **Then** it is refused.

---

### User Story 2 - The connection stays up (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a client-pinging venue, **When** the interval elapses, **Then** one ping is sent.
2. **Given** the same venue, **When** ticked inside the interval, **Then** nothing is sent.
3. **Given** a server-pinging venue, **When** ticked, **Then** the client never pings.
4. **Given** a server-pinging venue that was given an interval by mistake, **When** ticked, **Then** it still never pings.

---

### User Story 3 - A drop is noticed (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the venue that announces nothing, **When** it goes silent past its timeout, **Then** the session reconnects and counts it.
2. **Given** the venue that announces its closes, **When** it is quiet, **Then** the session does not second-guess it.
3. **Given** a quiet market with data still arriving, **When** ticked, **Then** nothing reconnects.
4. **Given** any reconnect, **When** it completes, **Then** a snapshot is needed again.

### Edge Cases

- **A reconnect inside the venue's connect limit.** Deferred and counted, not attempted.
- **A failed connect.** Counted and raised.
- **A venue with no measured lifetime.** Unmeasured, not unlimited.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: One session MUST drive all three venues, with differences as data.
- **FR-002**: Each venue's keepalive MUST be recorded as measured.
- **FR-003**: Client pings MUST follow a schedule, not every tick.
- **FR-004**: The keepalive direction MUST decide who pings.
- **FR-005**: A policy that cannot keep its own connection alive MUST be refused.
- **FR-006**: Silence past the timeout MUST be a drop only where the venue announces nothing.
- **FR-007**: Inbound data, including a pong, MUST reset the idle clock.
- **FR-008**: A throttled reconnect MUST be counted.
- **FR-009**: Any reconnect MUST require a fresh snapshot.
- **FR-010**: No test may open a socket.

### Key Entities

- **Venue policy**: what one venue expects of a client.
- **Stream session**: one subscription and its lifecycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Three venues, two keepalive directions, two distinct payloads.
- **SC-002**: A silent drop is inferred on one venue and not on the other.
- **SC-003**: Ticking five times inside an interval sends one ping.
- **SC-004**: Binance's five existing lifecycle tests pass against the shared session.
- **SC-005**: No test opens a socket.

## Assumptions

- **The connect limit is conservative rather than measured.** Establishing the
  real cap means exceeding it against a venue that has done nothing to deserve
  it.
- **A lifetime of `None` means unmeasured.** Binance closes at twenty-four
  hours; nothing similar was observed on the other two, which is not the same as
  there being nothing.

## Open Questions

- **Whether Bybit and OKX have a stream lifetime at all.** Observing one means
  holding a connection open for a day, which nothing has needed yet.
