---
traces: [REQ-WP-007]
status: draft
---

# Feature Specification: Signal state machine

**Feature Branch**: `wp-007-signal-state-machine`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-007 — implement long/short boundary + middle setups with deterministic transitions and tests.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Track a setup from approach to confirmation (Priority: P1)

Price enters a channel zone, the machine opens a candidate, and each subsequent
bar advances it along one lifecycle: approach, touch, rejection pending,
confirmed. Nothing skips a step, and the same bars always produce the same path.

**Why this priority**: This is the requirement. PRD §21.2 is explicit that a
zone touch is only a candidate, and the distinction between a candidate and a
signal is what stops the system alerting on every boundary graze.

**Independent Test**: Feed a bar sequence and channel snapshots; assert the exact
state path. Pure, no services.

**Acceptance Scenarios**:

1. **Given** price outside every zone, **When** a bar arrives, **Then** no candidate exists.
2. **Given** price entering the upper zone in a bearish channel of sufficient quality, **When** the bar closes, **Then** a short candidate opens in the approach state.
3. **Given** an approaching candidate, **When** price reaches the boundary, **Then** it advances to touch and not past it.
4. **Given** a touched candidate, **When** price closes back inside beyond the configured distance, **Then** it advances to rejection pending.
5. **Given** a rejection pending candidate, **When** confirmation is met, **Then** it advances to confirmed and records why.
6. **Given** the same bars fed twice, **When** the machine runs, **Then** the state paths are identical.

---

### User Story 2 - Refuse setups the channel does not support (Priority: P1)

A candidate only opens when the channel's own direction and quality justify it,
and an open candidate dies when the channel stops supporting it.

**Why this priority**: Equal to US1. PRD §1.2 states the product hypothesis as a
conditional probability — the edge, if any, is in the conditions, not in the
touch. A machine that opens candidates regardless of channel state is a boundary
detector wearing a signal's name.

**Independent Test**: Feed the same price action under channels of differing
direction and quality; candidates open in one case and not the other.

**Acceptance Scenarios**:

1. **Given** a channel whose quality is below the configured minimum, **When** price enters a zone, **Then** no candidate opens.
2. **Given** a channel whose slope does not support the direction, **When** price enters the matching zone, **Then** no candidate opens.
3. **Given** an open candidate, **When** the channel quality collapses below the minimum, **Then** it is invalidated with that reason recorded.
4. **Given** an open candidate, **When** price closes beyond the outer tolerance, **Then** it is invalidated with that reason recorded.

---

### User Story 3 - Give up on setups that go nowhere (Priority: P2)

A candidate that does not confirm within a configured number of bars expires,
rather than lingering and confirming on unrelated price action later.

**Why this priority**: PRD §21.6 requires it. Below US1 and US2 because an
unexpired candidate is a stale signal rather than a wrong one — but a candidate
that confirms twenty bars after its touch is describing a different event than
the one it opened for.

**Independent Test**: Open a candidate, feed the configured number of bars
without confirmation, observe expiry.

**Acceptance Scenarios**:

1. **Given** a candidate open for the configured number of bars without confirmation, **When** the next bar arrives, **Then** it expires.
2. **Given** an expired candidate, **When** later bars satisfy confirmation, **Then** it does not revive.
3. **Given** a confirmed candidate, **When** further bars arrive, **Then** expiry does not apply to it.

---

### Edge Cases

- What happens when price enters a zone and leaves within the same bar? The bar's close decides the state; a wick through a zone is an overshoot, which §21.1 tolerates within a configured bound.
- What happens when two candidates would open on the same bar in opposite directions? Impossible by construction — the zones do not overlap — but the machine holds at most one candidate per symbol and timeframe, so the question cannot arise.
- What happens when the channel snapshot is missing for a bar? No candidate opens and no open candidate advances; a signal derived from an absent channel is a signal derived from nothing.
- What happens to an open candidate when the channel is refitted and its boundaries move? The candidate tracks the current channel. It opened under conditions that may no longer hold, which is what invalidation is for.
- What happens when a candidate is confirmed and then price immediately invalidates it? The confirmed state is recorded and the candidate then resolves — a confirmation that happened is not unhappened by what follows. PRD §0.5.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The machine MUST implement the lifecycle PRD §21.2 gives: none, approach, touch, rejection pending, confirmed, alerted, and the terminal states resolved, invalidated and expired.
- **FR-002**: The machine MUST implement signal families A, B, C and D of PRD §21.1 — upper and lower boundary rejection, and middle-line continuation in both directions. Families E and F are out of scope per ADR-008.
- **FR-003**: Direction and boundary MUST be attributes of a candidate, not distinct states, per ADR-008.
- **FR-004**: A candidate MUST open only when the channel's slope supports the direction and its quality meets a configured minimum.
- **FR-005**: Zone membership MUST be decided by the channel position of PRD §13.10, using the zone bounds of §13.11 as configuration.
- **FR-006**: Transitions MUST be deterministic: identical inputs MUST produce identical state paths.
- **FR-007**: A transition MUST NOT skip a lifecycle step.
- **FR-008**: Every transition MUST record the bar that caused it and the reason.
- **FR-009**: A candidate MUST be invalidated when price closes beyond the configured outer tolerance, and the reason MUST be recorded.
- **FR-010**: A candidate MUST be invalidated when channel quality falls below the configured minimum, and the reason MUST be recorded.
- **FR-011**: A candidate MUST expire after a configurable number of bars without confirmation.
- **FR-012**: An expired or invalidated candidate MUST NOT revive.
- **FR-013**: Rejection detection MUST be pluggable, so the detectors PRD §21.3 lists can be added without changing the machine.
- **FR-014**: The machine MUST hold at most one candidate per symbol and timeframe.
- **FR-015**: When no channel snapshot is available for a bar, no candidate MUST open and no open candidate MUST advance.
- **FR-016**: Candidate state history MUST be immutable once recorded.
- **FR-017**: Every threshold MUST be configuration: zone bounds, minimum quality, slope threshold, rejection distance, outer tolerance, and expiry bars.

### Key Entities

- **Candidate**: a setup being tracked, with its direction, the boundary it concerns, its current state, and the transitions that brought it there.
- **Transition**: one state change, the bar that caused it, and why.
- **Rejection detector**: a pluggable rule deciding whether a touched candidate has rejected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A constructed approach-touch-reject-confirm sequence produces exactly that state path.
- **SC-002**: The same bars fed twice produce identical state paths and identical transition records.
- **SC-003**: Identical price action under a channel below the quality minimum opens no candidate.
- **SC-004**: Identical price action under a channel whose slope opposes the direction opens no candidate.
- **SC-005**: A candidate open for the configured number of bars without confirmation expires, and does not revive when confirmation conditions later occur.
- **SC-006**: Every terminal transition carries a reason that names its cause.
- **SC-007**: No transition skips a lifecycle step, across every test sequence.
- **SC-008**: A second rejection detector can be registered without modifying the machine.

## Assumptions

- The machine consumes finalized bars and the channel snapshots of REQ-WP-006. It computes neither.
- Alerting is out of scope. The lifecycle includes an alerted state because PRD §21.2 does, but delivering an alert is REQ-WP-008.
- Scoring is out of scope. PRD §22 defines a deterministic score for a confirmed signal; this feature decides *whether* a signal exists, not how good it is.
- Only the close-back-inside rejection detector is implemented. PRD §21.3 lists four; FR-013 makes the rest additions rather than rewrites, and building detectors whose confirmation features do not yet exist would produce untested paths.
- Order-flow and microstructure confirmation are out of scope: PRD §21.4's confirmation features depend on work packages not yet built.
- Every default here is a research default. PRD §13.11 says so of the zones, and §48 lists the questions that must be answered before any of this drives a decision.
