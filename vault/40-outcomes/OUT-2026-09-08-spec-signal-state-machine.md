---
id: OUT-2026-09-08-spec-signal-state-machine
step: spec
records: [REQ-WP-007]
commit: null
---

## What was done

Specified REQ-WP-007 as `specs/008-signal-state-machine/spec.md`: 17 functional
requirements, 8 success criteria.

## What was decided

- **The PRD describes the lifecycle twice, in two vocabularies.** §21.2 gives
  `NONE → APPROACH → TOUCH → REJECTION_PENDING → CONFIRMED → ALERTED →
  RESOLVED / INVALIDATED / EXPIRED`; §21.1 gives per-family names like
  `APPROACHING_UPPER` and `SIGNAL_SHORT` for what are plainly the same steps.
  [[ADR-008]] takes §21.2 as the machine and reads §21.1 as prose. Encoding
  per-family states would multiply the transition table by the number of
  families while the transitions themselves stay identical — and deterministic
  transitions, the thing this requirement actually asks for, are far easier to
  prove over one table. This is the fourth requirement running where the PRD
  says the same thing two ways or names a field without defining it.
- **Families E and F are out of scope.** REQ-WP-007 says "boundary + middle
  setups", which is A through D. Breakout-and-retest fires when the channel is
  *failing* rather than holding, and depends on channel transition semantics
  §21.1 only sketches. Building them here would mean specifying a channel
  lifecycle this requirement does not own.
- **A candidate only opens when the channel supports it** (FR-004). PRD §1.2
  states the hypothesis as a conditional probability: the edge, if any, is in
  the conditions rather than in the touch. A machine that opens on every zone
  entry is a boundary detector wearing a signal's name.
- **A confirmation that happened is not unhappened.** If price invalidates
  immediately after confirmation, the confirmed transition stays recorded and
  the candidate then resolves. PRD §0.5 forbids rewriting history, and a
  lifecycle that erased its own steps would be repainting in a different shape.
- **One rejection detector, not four.** PRD §21.3 lists close-back-inside, wick
  rejection, two-bar confirmation and microstructure-confirmed. Only the first
  is built; the others depend on §21.4's confirmation features, which need work
  packages that do not exist. FR-013 makes them additions rather than rewrites.

## What is still open

- **Three rejection detectors and all of §21.4's confirmation features.** They
  need order-flow and microstructure work not yet built.
- **Scoring is REQ-WP-007's neighbour, not its content.** PRD §22 defines a
  deterministic score for a confirmed signal; this feature decides whether a
  signal exists, not how good it is.
- **Alerting is REQ-WP-008.** The lifecycle carries an alerted state because
  §21.2 does; delivering an alert is elsewhere.
- **Every default is a research default**, as PRD §13.11 says of the zones and
  §48 says of the whole apparatus.
