---
traces: [REQ-WP-034]
status: draft
---

# Feature Specification: A stop update is announced with the risk it changed

**Feature Branch**: `wp-034-stop-alert`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-034 — Phase 7A's last deliverable.

## Context

PRD §44A.34 gives a message in which **every line is a transition**: old stop
against new stop, open risk `1.00R -> 0.28R`. A notification saying only where
the stop now sits reports what the chart already shows and withholds the one
thing it does not — how much risk just came off.

Two failures follow from that, and both produce a message that looks complete.

The first is losing the "from" half. `New stop: 112,060` is a true sentence, and
a reader cannot tell from it whether the stop moved by a tick or by most of the
risk.

The second is subtler and is [[REQ-WP-033]]'s: the "old stop" must be the stop
that was **in force**, not the last one the policy decided. A notification
announcing a move from a level the exchange never obeyed describes a change that
did not happen, in a message whose whole purpose is to say what changed.

§44A.34 ends with a rate limit: *do not notify for rejected micro-updates unless
debug mode is enabled*. Stop policies hold far more often than they move, and a
channel reporting every held micro-adjustment trains its reader to ignore it —
at which point the alerts that matter are lost exactly as silence would have
lost them, but expensively.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The message is the difference (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a stop that moved, **When** the message is rendered, **Then** it states both the old stop and the new one.
2. **Given** the same move, **When** open risk is rendered, **Then** it states the risk before and the risk after.
3. **Given** a move decided while an earlier update was still in flight, **When** the message is rendered, **Then** the old stop is the one that was in force.

---

### User Story 2 - Holds do not ring the phone (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a held proposal and debug off, **When** it is offered, **Then** nothing is sent and the suppression is recorded.
2. **Given** a refused proposal and debug off, **When** it is offered, **Then** nothing is sent and the suppression is recorded.
3. **Given** a held proposal and debug on, **When** it is offered, **Then** it is announced as a hold, never in the shape of an update.

---

### User Story 3 - One dispatcher, one audit (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a stop notification, **When** it is delivered, **Then** it retries, dead-letters and audits exactly as a signal alert does.
2. **Given** a transport that throws, **When** a stop notification is delivered, **Then** nothing escapes into the caller.
3. **Given** the existing signal alert, **When** it is rendered and delivered, **Then** nothing about it has changed.

### Edge Cases

- **A reason the renderer has never seen.** Shown, not dropped. A dropped reason is a veto that reads as no veto.
- **A proposal with no anchor.** The anchor block is absent, not rendered with a dash ([[ADR-016]]).
- **Open risk that did not change.** A move that tightens by nothing is not a move; if it is announced at all it says so rather than printing `0.40R -> 0.40R` as news.
- **A stop moved past entry.** Open risk after is zero and locked profit is real; zero here is a reading, not an absence.
- **Debug mode with nothing held.** No message. Debug widens what is announced; it does not invent events.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The message MUST state the old stop and the new stop.
- **FR-002**: The message MUST state open risk before and after, in R.
- **FR-003**: The old stop MUST be the stop that was in force when the move was decided.
- **FR-004**: A held or refused proposal MUST NOT be announced unless debug mode is on.
- **FR-005**: A suppression MUST be recorded, never silent.
- **FR-006**: With debug on, a hold MUST be rendered as a hold and never in the shape of an update.
- **FR-007**: The anchor and every reason MUST reach the message, including reasons the renderer does not recognise.
- **FR-008**: A block with no source MUST be absent rather than dashed.
- **FR-009**: Stop notifications MUST use the same dispatcher, retry policy and audit as signal alerts.
- **FR-010**: The existing signal alert MUST be unchanged.

### Key Entities

- **Stop update notification**: what changed about a position's risk, and why.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rendered message contains both stop levels and both risk figures.
- **SC-002**: A move decided while an earlier one was in flight names the in-force stop as the old one.
- **SC-003**: With debug off, holds and refusals produce zero deliveries and one audit record each.
- **SC-004**: A hold announced under debug shares no header with an update.
- **SC-005**: A transport exception produces an audit record and no raised exception.
- **SC-006**: Every existing alerting test passes unchanged.

## Assumptions

- **The notification is offered one proposal at a time.** What produces the proposals — a live engine or a replay — is the caller's, exactly as the signal alert does not know what produced its candidate.
- **The dispatcher becomes kind-agnostic.** Today it renders `Alert` directly. Two kinds of notification sharing one retry policy and one audit means the dispatcher depends on what every notification can do — identify itself, name its instrument, render, and link — rather than on one of them. The alternative, a second dispatcher, duplicates the retry and dead-letter logic that PRD §26.4 specifies once.
- **Debug mode is a flag on the gate**, not a global. §44A.35's configuration block is a phase-level concern; a boolean where the decision is made is the smallest thing that satisfies §44A.34.
- **Nothing constructs a dispatcher outside the alerting package today.** This lands in the same state the signal alert is already in — a mechanism waiting on the live mode §25.1 does not describe. Named rather than inherited quietly.

## Open Questions

- **When the notification fires** — at the decision, or at the modelled acknowledgement [[REQ-WP-033]] introduced. "STOP UPDATED" is past tense, which argues for the acknowledgement; §44A.35's `shadow` mode has no exchange to acknowledge anything, which argues it is the caller's choice. Left to the caller, and named here so the choice is visible.
- **Whether the deep link should open the position view** [[REQ-WP-032]] built, rather than the chart. §44A.34's button says `[ OPEN POSITION CHART ]`; nothing routes to a position yet.
