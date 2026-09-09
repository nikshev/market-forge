---
traces: [REQ-EXP-017]
status: draft
---

# Feature Specification: Adaptive stop-management policy comparison

**Feature Branch**: `exp-017-stop-policies`

**Created**: 2026-09-09

**Input**: REQ-EXP-017 — seven policies, twelve metrics, seven ablations, and a `NO_EDGE` verdict.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare seven policies on the exact same entry signals (Priority: P1)

Fixed initial stop; naive fixed-percent trailing; ATR/volatility trailing;
confirmed-swing structural; channel-conditioned structural; structural plus
order-flow confirmation; the full engine.

**Why this priority**: a stop study that let each policy pick its own entries
would be comparing entry selection and attributing the difference to stop
management.

**Acceptance Scenarios**:

1. **Given** the seven policies, **When** the comparison runs, **Then** each has a result, in the PRD's order.
2. **Given** any policy, **When** its trade count is read, **Then** it equals the number of entries.
3. **Given** two reports over different entries, **When** they are compared, **Then** the comparison is refused.
4. **Given** the same signal twice, **When** the comparison runs, **Then** it is refused.

---

### User Story 2 - Report all twelve primary metrics (Priority: P1)

Expectancy after fees and slippage, realized R, profit factor, stop-out rate,
premature-stop rate, give-back from MFE, MAE before the stop, median and 95th
percentile stop distance, holding time, stop-modification count, tail loss and
worst slippage, regime stability.

**Why this priority**: a stop policy has no single score. Widening a stop
improves four of these at once and destroys risk control, which PRD §44A.29 says
in as many words.

**Acceptance Scenarios**:

1. **Given** any policy, **When** its metrics are read, **Then** all twelve are present.
2. **Given** the premature-stop rate, **When** it is read, **Then** it comes from an object that also carries realized expectancy.
3. **Given** a policy that never stopped out, **When** its premature-stop rate is read, **Then** it is absent rather than zero.
4. **Given** a policy that never lost, **When** its profit factor is read, **Then** it is absent rather than zero or infinite.
5. **Given** the stop distances, **When** the median and the 95th percentile are read, **Then** they are two different numbers on a path where the distance grows.
6. **Given** a path that never stopped, **When** it is priced, **Then** it is marked out at the last price — fees charged, a stop's slippage not.

---

### User Story 3 - Ablate the engine and conclude (Priority: P1)

Seven capabilities removed one at a time, and a verdict the engine can fail.

**Why this priority**: the engine is the arm everybody wants to keep, so the
burden of proof is on it. EXP-017 says the experiment must be able to conclude
`NO_EDGE`.

**Acceptance Scenarios**:

1. **Given** the seven capabilities, **When** the ablations run, **Then** each is reported with its delta against the engine.
2. **Given** a capability whose removal helps, **When** its delta is read, **Then** it is negative — the report does not assume every capability earns its place.
3. **Given** an engine that beats the best simpler policy by the floor, **When** the verdict is read, **Then** it is `EDGE`.
4. **Given** an engine that does not, **When** the verdict is read, **Then** it is `NO_EDGE` and says a policy that only looks better is rejected.
5. **Given** the best simpler policy, **When** it is read, **Then** it is not the engine.

---

### Edge Cases

- What happens when a capability the engine does not have is ablated? Refused by name.
- What happens when no simpler policy could be scored? `NO_EDGE`, because the engine has nothing to beat.
- What happens to a policy that never exits? It is marked out, because a policy with no losses would otherwise win every comparison.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All seven policies MUST run over the same entries, in the PRD's order.
- **FR-002**: The entry set MUST carry a fingerprint, and a cross-report comparison over different entries MUST be refused.
- **FR-003**: A duplicated entry MUST be refused.
- **FR-004**: All twelve primary metrics MUST be reported.
- **FR-005**: The premature-stop rate MUST be a property of the object carrying realized expectancy, and MUST be absent over no stop-outs.
- **FR-006**: The profit factor over no losses MUST be absent.
- **FR-007**: The stop distance MUST be reported as a median and a 95th percentile of the distances actually observed.
- **FR-008**: A path that never stopped MUST be marked out at its last price, charged fees and not a stop's slippage.
- **FR-009**: All seven ablations MUST run, each with its delta against the engine.
- **FR-010**: An ablation delta MUST be allowed to be negative.
- **FR-011**: A capability outside the seven MUST be refused.
- **FR-012**: An ablation MUST change what the policy can see, not the policy's code.
- **FR-013**: The verdict MUST compare the engine against the best of the six simpler policies, excluding itself, and MUST be `NO_EDGE` when the margin is under the floor.
- **FR-014**: The improvement floor MUST be a required, positive argument.
- **FR-015**: The report MUST be deterministic.

### Key Entities

- **Capabilities**: one flag per ablation; an ablation is the full set without one.
- **Path point**: a decision instant plus the context the vetoes read.
- **Policy metrics**: one policy's twelve numbers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Seven results in the PRD's order; every trade count equals the entry count.
- **SC-002**: Two reports over different entries cannot be compared; a duplicated entry raises.
- **SC-003**: All twelve metrics present for the engine.
- **SC-004**: The premature-stop rate is not a field; it is absent over no stop-outs.
- **SC-005**: A policy that never lost has no profit factor.
- **SC-006**: The 95th-percentile stop distance exceeds the median for a fixed stop on a rising path.
- **SC-007**: A never-stopped path is priced at the last price; slippage changes nothing and fees lower it.
- **SC-008**: Seven ablations, each with a delta.
- **SC-009**: One ablation's delta is positive and another's is negative.
- **SC-010**: An unknown capability raises.
- **SC-011**: Switching a capability off removes its anchors, its veto or its noise floor from what the policy sees.
- **SC-012**: The engine is accepted on a shakeout fixture and rejected on a clean trend.
- **SC-013**: The best simpler policy is not the engine and is the strongest of the six.
- **SC-014**: The same entries give `EDGE` at one floor and `NO_EDGE` at a higher one.
- **SC-015**: Two runs produce equal reports.

## Assumptions

- **The entries, their paths and their anchors are supplied.** Detecting entries is the signal layer's job; this experiment manages what happens after one.
- **The replay is [[REQ-WP-020]]'s**, extended to record the walk ([[ADR-052]]). A second replay loop would be a second set of exit rules that only looked like the first.
- **Three capabilities are vetoes rather than levels.** The order-flow view, the turning-point forecast and the cross-venue context each say whether tightening is permitted here; none of them produces a price.
