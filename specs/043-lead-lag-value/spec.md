---
traces: [REQ-EXP-010]
status: draft
---

# Feature Specification: Cross-venue lead/lag value

**Feature Branch**: `exp-010-lead-lag-value`

**Created**: 2026-09-09

**Input**: REQ-EXP-010 — "measure whether divergence contains predictive value
after realistic latency/costs". Criteria derived on 2026-09-09.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate out of sample or not at all (Priority: P1)

A threshold chosen on the training segment, scored on the held-out one.

**Why this priority**: PRD §17.2 forbids converting a correlation into a trading
rule "without OOS validation", and this study is that validation. A threshold
chosen on the data it is scored on always looks profitable.

**Acceptance Scenarios**:

1. **Given** signals across the series, **When** the study runs, **Then** the threshold is chosen on the early segment and scored on the late one.
2. **Given** the in-sample report, **When** its trade count is read, **Then** it covers only in-sample signals.
3. **Given** signals on one side of the split only, **When** the study runs, **Then** it reports that it cannot validate rather than pretending.
4. **Given** thresholds that score equally, **When** one is chosen, **Then** it is the first, not the last tried.

---

### User Story 2 - Charge for latency and costs (Priority: P1)

The entry is delayed by a stated latency, and the result is net of fees and
slippage.

**Why this priority**: EXP-010 names both in its one sentence. A study that
enters on the signal's own bar is measuring a trade nobody could place.

**Acceptance Scenarios**:

1. **Given** a move that is over in two bars, **When** the latency is five, **Then** the measured edge falls.
2. **Given** the study's signature, **When** it is inspected, **Then** the latency has no default.
3. **Given** a negative latency, **When** it is passed, **Then** it is refused.
4. **Given** higher costs, **When** the study is rerun, **Then** the out-of-sample result falls.
5. **Given** no cost model, **When** the study is requested, **Then** it is refused before anything is scored.

---

### User Story 3 - Conclude nothing, when there is nothing (Priority: P1)

`NO_EDGE` is returned, and the study stays off the signal path.

**Why this priority**: [[ADR-042]]'s pattern, and [[ADR-040]]'s import ban. This
module is the evidence §17.2 demands, not a licence to trade on it.

**Acceptance Scenarios**:

1. **Given** signals pointing the wrong way, **When** the study runs, **Then** the verdict is `NO_EDGE` and nothing is raised.
2. **Given** outcomes that are all ambiguous, **When** the study runs, **Then** it reports rather than raising out of the metric layer.
3. **Given** the signal, alerting, stop and extrema packages, **When** their imports are inspected, **Then** none reaches this module.

---

### Edge Cases

- What happens when the divergence points the right way but the move is smaller than the costs? The verdict is `NO_EDGE`, which is the honest reading: the prediction was right and unprofitable.
- What happens to a signal too close to the end of the series? It has no fill or no horizon and is dropped, rather than resolved as a timeout.
- What happens when a short signal is given? Its target is below the fill and its stop above. A study whose fixtures are all long would never see the difference.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The threshold MUST be chosen on the in-sample segment only.
- **FR-002**: The verdict MUST come from the out-of-sample segment.
- **FR-003**: Signals on one side of the split MUST produce a stated refusal to validate.
- **FR-004**: Equal-scoring thresholds MUST resolve to the first tried.
- **FR-005**: The entry MUST be delayed by the stated latency.
- **FR-006**: The latency MUST have no default and MUST refuse a negative value.
- **FR-007**: Fees and slippage MUST be applied, and a missing cost model MUST be refused before anything is scored.
- **FR-008**: The direction MUST set the target and stop on the correct sides.
- **FR-009**: An all-ambiguous set MUST report rather than raise.
- **FR-010**: The verdict MUST be `EDGE` only on a positive out-of-sample result.
- **FR-011**: No signal-path module may import this study.
- **FR-012**: The result MUST be deterministic.

### Key Entities

- **Divergence signal**: an instant, a magnitude, and the direction the caller reads from it.
- **Result**: the verdict, the chosen threshold, both reports, and the signal counts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A predictive divergence reaches `EDGE`; a wrong-way one does not.
- **SC-002**: The in-sample trade count covers only in-sample signals.
- **SC-003**: One-sided signals refuse to validate.
- **SC-004**: Equal thresholds resolve to the first.
- **SC-005**: Latency reduces the measured edge.
- **SC-006**: The latency has no default; a negative one refuses.
- **SC-007**: Higher costs lower the result; no cost model refuses.
- **SC-008**: A short signal is traded as a short.
- **SC-009**: An all-ambiguous set reports `NO_EDGE`.
- **SC-010**: No signal-path module imports the study.
- **SC-011**: Two runs produce equal results.

## Assumptions

- **The signals are supplied.** [[REQ-WP-016]] computes the basis and says nothing about direction; reading a divergence as a long or a short is the caller's.
- **The exit rule is fixed and symmetric.** EXP-010 asks whether the divergence predicts direction, not what the best exit is.
- **Latency is measured in bars.** A sub-bar latency needs the tick replay §40 mentions and this study does not have.
