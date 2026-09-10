---
id: OUT-2026-09-10-requirement-outage-alerts
step: requirement
records: [REQ-WP-035]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-035.md`, extracted from PRD §32 and §45's
Phase 8. One of [[REQ-PHASE-8]]'s seven open deliverables.

## What was decided

- **Four states, not a boolean.** §32's eligibility rules sit directly beneath
  its state list and treat DEGRADED and STALE differently — a degraded
  confirmation lowers confidence, a stale book disqualifies a signal outright.
  Collapsing them into "unhealthy" would make the rules above unimplementable
  while looking like a simplification.
- **The recovery is half the requirement.** Silence after a failure notice reads
  as "still down" and as "nobody is watching" equally well. It is also the half
  a system reliably forgets, because a recovery feels like the absence of a
  problem rather than an event — which is exactly why it is written into
  acceptance rather than left to good sense.
- **Transitions, not states.** A feed hovering at a threshold alerts on every
  observation, and a channel that cries constantly loses the outage as
  thoroughly as silence would, at greater cost.
- **An operational alert must not look like a trading signal.** They travel the
  same wire to the same reader, who acts on one and investigates the other.
  Distinguishable in the message, not merely by which code path made it.
- **Thresholds are arguments.** §32 lists nine metrics and no values, which is
  §13.11's situation exactly: a constant written here would be a research
  default wearing a decision's clothes.

## What is still open

- **Nothing produces a health state.** No connector runs, so nothing observes a
  reconnect count or a gap rate. This will carry and announce the state, as
  [[REQ-WP-031]] carried a ratio nothing writes.
- **§33's metrics export and dashboards** are a separate Phase 8 deliverable and
  stay separate: this is the alert, not the instrumentation.
- **Whether `BookHealth` should become one of these states** rather than sit
  beside them. It answers a narrower question — is this book trustworthy — and
  folding it in may or may not be right.
