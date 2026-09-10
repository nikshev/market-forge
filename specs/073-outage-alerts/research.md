# Phase 0 — Research

## 1. What does an absent reading mean?

**Decision**: not "within its limit". An assessment with no readings at all is
not GOOD, and says nothing was reported.

**Rationale**: the failure this whole requirement exists for is a feed that has
gone so wrong it cannot report. A default of GOOD is exactly what silences that
case, and the silence looks identical to a healthy system. Every other absence
in this repository is a value nobody supplied; this one is a symptom.

**Alternatives considered**: treating an absent metric as GOOD for that
dimension and requiring at least one reading. Rejected — it makes a feed that
reports only its easiest metric indistinguishable from one reporting all of
them.

## 2. GOOD from nothing, or a state of its own?

**Decision**: reuse INVALID.

**Rationale**: INVALID means the data cannot be trusted, and an assessment with
no inputs is precisely that. A fifth state (`UNKNOWN`) would have to be
threaded through §32's eligibility rules, which name four, and every consumer
would need a rule for it that the PRD does not give. The reason string carries
the difference between "invalid because gappy" and "invalid because silent",
which is what a reader needs and what a state name would only approximate.

## 3. When does an alert fire?

**Decision**: on a change of state. First sight in a bad state alerts; first
sight in GOOD does not.

**Rationale**: alerting on state floods, and a channel that cries constantly
loses the outage as thoroughly as silence would. The two first-sight rules are
asymmetric because the situations are: waiting for a prior good state stays
silent through an outage that began before the process did, while announcing a
recovery from nothing reports an outage that never happened.

## 4. How are the states compared?

**Decision**: ranked, and the rank is tested.

**Rationale**: "the worst one decides" is a comparison, not a conditional chain
that a tenth metric would have to be threaded through. A mis-ordered rank makes
a stale feed outrank an invalid one and the assessment still returns a plausible
state, so the ordering gets its own test rather than being implied by the ones
that use it.

## 5. Where does the duration come from?

**Decision**: the difference between the instant the state went bad and the
instant it came back, both supplied.

**Rationale**: no clock anywhere ([[ADR-018]]), so a replay produces the same
message. Zero is expressible and true — bad and good within one instant — and is
not the same as absent.
