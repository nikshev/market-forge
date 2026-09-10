---
traces: [REQ-WP-033]
status: draft
---

# Feature Specification: A stop update is not effective until it is acknowledged

**Feature Branch**: `wp-033-stop-latency`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-033 — one of Phase 7A's two remaining deliverables.

## Context

PRD §44A.27 states the rule and supplies its own failing example:

    Stop updates are effective only after modeled decision + computation +
    network/exchange latency.

        signal computed at 10:15:00.100
        stop modification ack at 10:15:00.260
        market touch at 10:15:00.180

    The new stop was not yet active.

The replay applies a decided stop from the instant it was decided. In the PRD's
own example that means the touch at `.180` is evaluated against a level the
exchange had not yet acknowledged — a position reported as protected by a stop
that did not exist.

**The bias does not run one way**, and that is the argument for modelling the
gap rather than reasoning about it. An instantly-effective tightening sometimes
exits earlier than reality would have, and sometimes locks a profit reality
would have given back. Neither direction is "conservative", so no amount of
argument makes the current behaviour safe.

The rule creates its own ambiguity, and §44A.27 says what to do about that too:
where ordering cannot be known, mark it ambiguous or resolve it by a predeclared
conservative rule — **never by whichever ordering gives better PnL.**

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A decided stop is not yet an active stop (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a stop decided at `t` and a latency `L`, **When** the market touches that level before `t + L`, **Then** the position is evaluated against the stop that was active, not the decided one.
2. **Given** the same path after `t + L`, **When** the market touches the new level, **Then** it is evaluated against the new stop.
3. **Given** the PRD's own example, **When** it is replayed, **Then** the touch at `.180` does not exit on a stop acknowledged at `.260`.

---

### User Story 2 - The latency is declared, not assumed (Priority: P1)

**Acceptance Scenarios**:

1. **Given** no explicit choice, **When** a replay runs, **Then** it runs under a stated non-zero latency, not an instantaneous one.
2. **Given** a caller who wants the instantaneous case, **When** they ask for it, **Then** it is expressible and produces the results the replay produced before this feature existed.
3. **Given** a report, **When** it is read, **Then** it names the latency it was produced under.

---

### User Story 3 - Ambiguity is resolved by rule, not by outcome (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a touch at exactly the acknowledgement instant, **When** it is evaluated, **Then** a single predeclared rule decides, and the rule is stated where it is applied.
2. **Given** two paths where that rule pays differently, **When** each is replayed, **Then** the rule resolves both the same way.

### Edge Cases

- **A latency longer than the whole path.** No update ever becomes effective. The position runs on its initial stop, which is a true statement about a system that decides faster than it can be obeyed.
- **Several decisions inside one latency window.** Each becomes effective at its own acknowledgement instant; a later decision does not cancel an earlier one that has already landed.
- **A zero latency.** Expressible, and produces exactly the prior behaviour. It is not the default.
- **The naive baselines.** They send stop updates too. A baseline obeyed instantly while the adaptive policy waits is not a comparison of policies.
- **A latency supplied as a total with no breakdown.** Accepted; the parts the PRD gives no figure for are stated as absent rather than guessed at.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A stop decided at `t` MUST NOT be effective before `t + latency`.
- **FR-002**: A trigger inside that window MUST be evaluated against the stop that was active.
- **FR-003**: Latency MUST be a declared value carried by the replay, not a constant inside it.
- **FR-004**: The default MUST be non-zero, and MUST be traceable to the only figure the PRD supplies.
- **FR-005**: Zero latency MUST be expressible and MUST reproduce the prior results exactly.
- **FR-006**: A comparison report MUST state the latency it was produced under.
- **FR-007**: Every policy in one comparison, baselines included, MUST run under the same latency.
- **FR-008**: A touch at exactly the acknowledgement instant MUST be resolved by one predeclared rule, stated where it is applied, and never by which reading pays better.
- **FR-009**: Latency MUST be expressible as named contributions, with the ones nobody has measured stated as absent rather than invented.

### Key Entities

- **Activation latency**: the modelled delay between deciding a stop and the exchange obeying it, in named parts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Replaying the PRD's example produces no exit at the touch that precedes the acknowledgement.
- **SC-002**: A replay under zero latency reproduces the outcomes recorded before this feature, field for field.
- **SC-003**: The default latency is non-zero and the report names it.
- **SC-004**: Two paths on which the tie rule pays differently resolve the same way.
- **SC-005**: A latency exceeding the path leaves the position on its initial stop.
- **SC-006**: Every existing replay test still states what it assumes about activation.

## Assumptions

- **The latency is modelled, and the name says so**, as [[REQ-WP-020]]'s `CostModel.slippage_bps` does. A constant is not a measurement; the honest version needs acknowledgement timestamps from a venue, and none exist.
- **The default is the PRD's own gap**: 160 ms between "signal computed" and "stop modification ack". It is an example, not a measurement, and it is the only number the PRD gives. Recording it as the network/exchange contribution with the decision and computation legs at zero is what that example actually supports — the total is therefore a floor, and is documented as one.
- **Intra-bar trigger/target ordering is out of scope here** because it cannot arise: a `PricePoint` carries one price, so no ordering exists to choose. §44A.27's rule about it is honoured where this feature *does* create an ordering question — the tie at the acknowledgement instant — rather than asserted vacuously over a case the model cannot express. This is stated rather than quietly skipped.

## Open Questions

- **Whether decision and computation latency should ever be non-zero by default.** They are real and unmeasured; guessing them would put an invented number where a floor is honest.
- **Whether an ambiguous outcome should be excludable from a comparison** rather than resolved conservatively. The conservative rule is enough for the tie this feature creates; a richer ambiguity would need somewhere to go in the report.
