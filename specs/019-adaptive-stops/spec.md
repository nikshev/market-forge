---
traces: [REQ-WP-020, REQ-BIAS-009]
status: draft
---

# Feature Specification: Adaptive stop management

**Feature Branch**: `wp-020-adaptive-stops`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-020 — PRD §44A's adaptive stop engine, scoped to its own
"Done when" criteria and §44A.39's acceptance. REQ-BIAS-009 — fees and slippage
must be included in economic evaluation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Never widen the accepted risk (Priority: P1)

A stop update may tighten risk. It may never loosen it.

**Why this priority**: PRD §44A.2 states the rule and its exception in one
breath: "The adaptive stop may tighten risk but must never silently widen the
maximum risk beyond the accepted initial-risk contract... Any policy that
permits widening must be a separate explicitly enabled research policy and must
never be enabled in production by default."

**Independent Test**: Propose stops from anchors on both sides of the current
stop and assert only the tightening ones are taken.

**Acceptance Scenarios**:

1. **Given** a long position, **When** a proposal is below the current stop, **Then** the current stop stands.
2. **Given** a short position, **When** a proposal is above the current stop, **Then** the current stop stands.
3. **Given** either side, **When** a proposal tightens, **Then** it is taken and its anchor is recorded.
4. **Given** a proposal that would exceed the accepted initial risk, **When** it is evaluated, **Then** it is refused whatever else favours it.

---

### User Story 2 - Never move a stop on a swing that had not been confirmed (Priority: P1)

A structural anchor may only be used at or after the moment the system could
have known it.

**Why this priority**: PRD §44A.3 — "All inputs must be available according to
`available_at`; no future-confirmed swing may be used before its `known_at`."
REQ-WP-019 built exactly that timestamp, and this is what it was for.

**Independent Test**: A confirmed extremum whose `known_at` is after the
decision instant, and an assertion that no proposal uses it.

**Acceptance Scenarios**:

1. **Given** a swing confirmed after the decision instant, **When** anchors are built, **Then** it is absent.
2. **Given** the same swing once its `known_at` has passed, **When** anchors are built, **Then** it is present.
3. **Given** any proposal, **When** its anchor is read, **Then** the anchor's `known_at` is at or before the decision instant.

---

### User Story 3 - Move for a reason, or not at all (Priority: P1)

Every stop movement names a structural anchor and reason codes. A policy that
concludes the stop should not move says so.

**Why this priority**: §44A.39 requires both — "every movement has a structural
anchor and reason codes" and "policy may conclude that leaving the original
stop unchanged is optimal for a position". A stop that drifts without a reason
is the blind price-following the same section forbids.

**Acceptance Scenarios**:

1. **Given** a movement, **When** the proposal is read, **Then** it names its anchor and at least one reason code.
2. **Given** no qualifying anchor, **When** a proposal is made, **Then** it holds the current stop and says why.
3. **Given** a proposal within the improvement threshold, **When** hysteresis is applied, **Then** it holds and records the churn reason.
4. **Given** a data-quality freeze, **When** a proposal is made, **Then** it holds and names the freeze.

---

### User Story 4 - Keep the stop clear of ordinary noise (Priority: P2)

A stop is placed at least a configurable noise distance from the market and
from its anchor.

**Why this priority**: PRD §44A.8 and §44A.9, and §44A.29's premature-stop
metric exists because of it — "the user's concern that a trailing stop gets
taken out by ordinary price noise".

**Acceptance Scenarios**:

1. **Given** a volatility measure, **When** the noise distance is computed, **Then** it uses only data at or before the decision instant.
2. **Given** an anchor closer to the market than the noise distance, **When** the proposal is made, **Then** it is pushed back or held.
3. **Given** a stop that would sit beyond the market price, **When** it is evaluated, **Then** it is refused.

---

### User Story 5 - Compare against naive baselines, with costs (Priority: P1)

A counterfactual replay reports the adaptive policy beside a fixed-percent and
an ATR trailing stop, with realized R net of fees and modelled slippage, and
the premature-stop rate.

**Why this priority**: REQ-WP-020's own "Done when" asks for the OOS report and
the premature-stop metric, and §44A.39 requires a naive baseline in the
comparison. PRD §41 rule 9 — "Fees/slippage must be included in economic
evaluation" — is what makes the R figures legitimate.

**Independent Test**: A scripted price path, each policy replayed over it, and
hand-computed R.

**Acceptance Scenarios**:

1. **Given** a price path, **When** each policy is replayed, **Then** each reports its exit and realized R.
2. **Given** a realized exit, **When** R is computed, **Then** fees and modelled slippage are subtracted.
3. **Given** a stop that triggered before the original target was reached, **When** the metric is computed, **Then** it counts toward the premature-stop rate.
4. **Given** a report, **When** it is read, **Then** it carries the premature-stop rate beside realized R, never alone.
5. **Given** the same path replayed twice, **When** the results are compared, **Then** they are identical.

---

### Edge Cases

- What happens when the hard stop and the adaptive stop conflict? The hard stop wins. §44A.2: "The hard stop must never depend on the availability of the adaptive engine."
- What happens when a stop is proposed exactly at the current stop? It holds, and the reason says no improvement — an update with no effect still costs an exchange call.
- What happens when the position has no initial stop? Proposals are refused: the initial-risk contract is what every guard is measured against, and without it there is nothing to enforce.
- What happens when price gaps through the stop? The realized exit is the first executable price, not the stop price, and the slippage is recorded. §44A.23: "A stop price is not a guaranteed fill price."
- What happens when every anchor is stale? The proposal holds with a freeze reason rather than falling back to a price-derived stop, which would be the blind following §44A.39 forbids.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A proposal MUST never widen risk: for a long, the new stop is at or above the current; for a short, at or below.
- **FR-002**: A proposal MUST never exceed the position's accepted initial risk.
- **FR-003**: An anchor MUST NOT be used before its `known_at`.
- **FR-004**: Every proposal MUST name its anchor and at least one reason code, including proposals that hold.
- **FR-005**: A proposal within the configured improvement threshold MUST hold, with a churn reason.
- **FR-006**: A cooldown MUST prevent a second movement within a configured event-time interval.
- **FR-007**: A data-quality freeze MUST hold the stop and name the freeze.
- **FR-008**: The noise distance MUST be computed from data at or before the decision instant.
- **FR-009**: A stop beyond the market price MUST be refused.
- **FR-010**: A position lifecycle MUST follow PRD §44A.4's states, and every transition MUST be recorded.
- **FR-011**: The stop path MUST be immutable once recorded.
- **FR-012**: A replay MUST report the adaptive policy beside a fixed-percent and an ATR trailing baseline.
- **FR-013**: Realized R MUST be net of fees and modelled slippage.
- **FR-014**: The realized exit MUST use the first executable price, not the requested stop price.
- **FR-015**: The report MUST carry the premature-stop rate, and MUST NOT present it without realized R.
- **FR-016**: Two replays of one path MUST give identical results.
- **FR-017**: No module may consult a system clock.
- **FR-018**: No default policy path may derive a stop from price alone, without a structural anchor.

### Key Entities

- **Position state**: side, entry, the accepted initial risk, and where the stop is now.
- **Stop anchor**: a structural level, what produced it, and when it became knowable.
- **Stop proposal**: a price or a hold, its anchor, and its reason codes.
- **Policy outcome**: what a replay of one policy over one path produced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A widening proposal is refused on both sides.
- **SC-002**: A proposal exceeding the initial-risk contract is refused.
- **SC-003**: An anchor whose `known_at` is after the decision instant never appears in a proposal.
- **SC-004**: Every proposal, including holds, carries an anchor reference and a reason code.
- **SC-005**: A sub-threshold improvement holds; a cooldown holds; a freeze holds.
- **SC-006**: The noise distance ignores data after the decision instant.
- **SC-007**: A replay's realized R matches hand-computed values net of fees and slippage.
- **SC-008**: The premature-stop rate matches a hand-counted scenario.
- **SC-009**: Two replays of one path are identical.
- **SC-010**: No module references a system clock, and no default path proposes a stop without an anchor.

## Assumptions

- **PRD §44A items 16 to 18 are out of scope**: the UI stop path, the Telegram stop-update event, and the exchange reconciliation interface. §44A.39 is explicit that "live mode requires a separate execution-security/reconciliation acceptance process".
- **§44A.26's ML research targets are not built.** §44A.39 ends "no ML component is required for correctness", and this is the deterministic engine that statement is about.
- **Slippage is modelled, not measured.** A configurable basis-point cost against the executable price, applied on the adverse side. Real slippage needs the order book at stop time (REQ-WP-004 supplies a book; a fill model does not exist).
- **DeFi and cross-venue context (§44A.15) is absent**, needing REQ-WP-014/015 and REQ-WP-016.
- **One position at a time.** Portfolio-level risk is not in REQ-WP-020's scope.
