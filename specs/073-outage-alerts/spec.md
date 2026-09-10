---
traces: [REQ-WP-035]
status: draft
---

# Feature Specification: A feed going quiet is announced, and so is its coming back

**Feature Branch**: `wp-035-outage-alerts`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-035 — one of Phase 8's seven deliverables.

## Context

PRD §32 gives four health states — GOOD, DEGRADED, STALE, INVALID — and, in the
lines directly beneath them, eligibility rules that treat them differently: a
degraded confirmation lowers confidence, a stale book disqualifies a signal
outright. §45's Phase 8 asks for alerting on the outages those states describe.

Three things can go wrong, and each produces a system that looks monitored.

**A metric nobody reported reads as healthy.** This is the most dangerous shape
of "absent is not zero" in the whole document: a monitoring input that stops
arriving is indistinguishable, to a naive assessment, from one arriving with
good news. A feed that has gone so wrong it cannot even report is the case the
alerting exists for, and it is the case a default of GOOD silences.

**An outage alert with no all-clear.** Silence after a failure notice reads as
"still down" and as "nobody is watching" equally well. The recovery is the half
that lets somebody stop looking, and the half a system reliably forgets, because
a recovery feels like the absence of a problem rather than an event.

**Alerting on state rather than on change.** A feed hovering at a threshold
alerts on every observation, and a channel that cries constantly loses the
outage as thoroughly as silence would, at greater cost.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Four states, kept apart (Priority: P1)

**Acceptance Scenarios**:

1. **Given** readings within every limit, **When** health is assessed, **Then** it is GOOD.
2. **Given** a stale feed and a gappy one, **When** each is assessed, **Then** they are STALE and INVALID respectively, never one "unhealthy".
3. **Given** several problems at once, **When** health is assessed, **Then** the worst one decides, and the reason says which.

---

### User Story 2 - Nothing reported is not good news (Priority: P1)

**Acceptance Scenarios**:

1. **Given** no readings at all, **When** health is assessed, **Then** it is not GOOD, and the reason says nothing was reported.
2. **Given** some readings and one absent, **When** health is assessed, **Then** the absent one is not treated as within its limit.

---

### User Story 3 - Transitions, both ways (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a feed turning bad, **When** it is observed, **Then** one alert is raised.
2. **Given** the same bad state observed again, **When** it is observed, **Then** no further alert is raised.
3. **Given** a feed returning to GOOD, **When** it is observed, **Then** a recovery is announced, naming how long it was bad.
4. **Given** a feed moving from DEGRADED to INVALID, **When** it is observed, **Then** that is a new alert, because it is a new fact.

---

### User Story 4 - Not mistakable for a trade (Priority: P2)

**Acceptance Scenarios**:

1. **Given** an operational alert, **When** it is read, **Then** it is distinguishable from a trading signal in the message itself.
2. **Given** either kind, **When** it is delivered, **Then** it retries, dead-letters and audits identically.

### Edge Cases

- **A feed seen for the first time in a bad state.** An alert: there is no prior good state to transition from, and waiting for one would stay silent through an outage that began before the process did.
- **A feed seen for the first time as GOOD.** No alert. Announcing a recovery from nothing would report an outage that never happened.
- **A recovery for a feed nobody ever alerted about.** Not announced, for the same reason.
- **Thresholds a caller left out.** Every limit is an argument with a stated default; §32 supplies nine metrics and no values, so a constant written into the assessment would be a research default wearing a decision's clothes.
- **A duration of zero.** A feed bad and good within one observation instant reports zero, which is true, and is not the same as absent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Health MUST be one of GOOD, DEGRADED, STALE, INVALID, and the three bad ones MUST remain distinguishable wherever carried.
- **FR-002**: An assessment with no readings MUST NOT be GOOD, and MUST say nothing was reported.
- **FR-003**: An absent individual reading MUST NOT count as within its limit.
- **FR-004**: Where several readings are bad, the worst MUST decide, and the reason MUST name it.
- **FR-005**: An alert MUST be raised on a change of state, never on each observation of an unchanged one.
- **FR-006**: A return to GOOD MUST be announced, with the duration it was bad.
- **FR-007**: A first observation in a bad state MUST alert; a first observation in GOOD MUST NOT.
- **FR-008**: Thresholds MUST be arguments.
- **FR-009**: An operational alert MUST be distinguishable from a trading signal within the message.
- **FR-010**: Operational alerts MUST use the same dispatcher, retry policy and audit as every other notification.
- **FR-011**: Nothing about the existing notifications MUST change.

### Key Entities

- **Feed health**: what a data source is currently worth, and why.
- **Health transition**: the only thing worth saying out loud.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An empty set of readings assesses as not GOOD with a stated reason.
- **SC-002**: STALE and INVALID inputs produce two different states and two different messages.
- **SC-003**: The same bad state observed three times produces one alert.
- **SC-004**: A recovery message names the feed and the duration.
- **SC-005**: A DEGRADED to INVALID move produces a second alert.
- **SC-006**: An operational message and a signal message share no header.
- **SC-007**: Every existing alerting test passes unchanged.

## Assumptions

- **This is the alert, not the instrumentation.** §33's Prometheus metrics and
  dashboards are a separate Phase 8 deliverable and stay separate.
- **Nothing produces a health reading yet.** No connector runs, so nothing counts
  a reconnect or a gap. This carries and announces the state, as [[REQ-WP-031]]
  carried a ratio nothing writes.
- **The modelled metrics are the subset of §32's nine that a threshold can act
  on today** — reconnects, gap rate, stale time, missing bars, duplicate rate.
  Chain RPC lag, subgraph indexing lag and insert delay belong to systems that do
  not exist here, and adding fields for them would suggest something watches them.
- **`BookHealth` stays where it is.** It answers a narrower question — is this
  book trustworthy — and folding it in is a decision for whoever has both a book
  and a feed to reconcile.

## Open Questions

- **Whether a DEGRADED feed should ever escalate on duration alone.** A feed
  degraded for an hour is arguably a different fact from one degraded for a
  second, and nothing here says so.
- **Where the eligibility rules live.** §32 states them; no signal path consumes
  a health state yet.
