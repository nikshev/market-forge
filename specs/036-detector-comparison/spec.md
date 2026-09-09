---
traces: [REQ-EXP-003]
status: draft
---

# Feature Specification: Rejection detector comparison

**Feature Branch**: `exp-003-detector-comparison`

**Created**: 2026-09-09

**Input**: REQ-EXP-003 — four detectors, criteria derived on 2026-09-09 (see
`docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare all four, including the one that cannot run (Priority: P1)

Every detector EXP-003 names appears, and the one whose inputs do not exist says
so.

**Why this priority**: three of the four are buildable from a bar and a channel.
The fourth needs order flow, which the detector interface does not carry, and
scoring it anyway would compare a detector that never saw its own inputs against
three that did.

**Acceptance Scenarios**:

1. **Given** the four detectors, **When** the comparison runs, **Then** each has an entry.
2. **Given** the order-flow detector, **When** its entry is read, **Then** it carries the reason it could not run and no scores.
3. **Given** the unavailable detector, **When** the ranking is read, **Then** it is not in it.
4. **Given** a detector that confirms nothing, **When** its entry is read, **Then** it says so rather than reporting zero.

---

### User Story 2 - Measure the four ways a detector can be wrong (Priority: P1)

Confirmation count, median lag, the share later invalidated, and expectancy
after costs.

**Why this priority**: a detector can be right on any three of these and wrong
on the fourth, and collapsing them into one score hides which.

**Acceptance Scenarios**:

1. **Given** a detector that confirmed setups, **When** its entry is read, **Then** all four metrics are present.
2. **Given** a permissive detector and a strict one, **When** their lags are compared, **Then** the permissive one confirms sooner.
3. **Given** confirmations the market later invalidated, **When** the share is computed, **Then** it reflects them.
4. **Given** a candidate invalidated before it confirmed, **When** the share is computed, **Then** it is not counted.
5. **Given** expectancy, **When** it is computed, **Then** it uses only out-of-sample confirmations.

---

### User Story 3 - Compare the detectors, not a copy of the engine (Priority: P1)

Each detector runs inside the production signal machine.

**Why this priority**: PRD §25.2 forbids a second implementation of strategy
logic, and a comparison that reimplemented the lifecycle would be measuring its
own copy.

**Acceptance Scenarios**:

1. **Given** the comparison's source, **When** it is inspected, **Then** it builds no transition and drives no state of its own.
2. **Given** the production default detector, **When** the set is read, **Then** it is among them.
3. **Given** one input, **When** the comparison runs twice, **Then** the reports are equal.

---

### Edge Cases

- What happens when a stateful detector is used twice? The runner copies its machine per run, so the second run does not inherit the first's memory. Two runs over one series produce one report.
- What happens when the wick detector sees a bar with no body? A doji that spiked through the boundary and came back is a rejection, not a division by zero.
- What happens when a long setup is tested? Its wick points down. A detector reading the upper wick for both directions passes every short-only fixture and inverts on half the setups it will meet.
- What happens when no detector confirms anything? Every entry says so, the ranking is empty, and the report is a finding about the series.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All four detectors MUST appear in the report.
- **FR-002**: A detector whose inputs do not exist MUST be reported with the reason and MUST NOT be scored or ranked.
- **FR-003**: Each detector MUST run inside the production `SignalMachine`.
- **FR-004**: For each detector that confirmed, the report MUST carry confirmation count, median lag in bars, the share later invalidated, and expectancy in R after costs.
- **FR-005**: The lag MUST be measured from the candidate's opening to its confirmation.
- **FR-006**: The later-invalidated share MUST count only invalidations after a confirmation.
- **FR-007**: Expectancy MUST use only out-of-sample confirmations.
- **FR-008**: The wick detector MUST read the wick on the side the setup rejects from, and MUST treat a bodyless bar with a wick as a rejection.
- **FR-009**: The two-bar detector MUST NOT answer before it has a previous close, and MUST respect direction.
- **FR-010**: The ranking MUST be by expectancy, ties broken by name, excluding the unscored.
- **FR-011**: The comparison MUST be refused without a cost model.
- **FR-012**: The report MUST be deterministic.

### Key Entities

- **Detector entry**: one detector's four metrics, or why it has none.
- **Candidate life**: one candidate's opening, confirmation and whether it was later invalidated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Four entries; the unavailable one carries its reason and is unranked.
- **SC-002**: A detector that confirms nothing reports its reason, not zero.
- **SC-003**: All four metrics present for a detector that traded.
- **SC-004**: The permissive detector's median lag is no greater than the strict one's, and no lag is zero.
- **SC-005**: A taken-back confirmation raises the share; one invalidated before confirming does not.
- **SC-006**: Expectancy counts fewer trades than the run has confirmations.
- **SC-007**: The wick detector reads the correct side and handles a bodyless bar.
- **SC-008**: The two-bar detector is silent on its first bar and direction-aware.
- **SC-009**: The comparison's source builds no transition.
- **SC-010**: Two runs produce equal reports.
- **SC-011**: No cost model refuses.

## Assumptions

- **The order-flow detector stays unbuilt here.** Wiring order flow into the detector interface is a change to [[REQ-WP-007]]'s protocol and [[REQ-WP-011]]'s features, not to this experiment.
- **The channel model is held fixed.** EXP-003 varies the detector; [[REQ-EXP-001]] varies the model.
- **The exit rule is the same one [[REQ-EXP-001]] uses**, so the two experiments' expectancies mean the same thing.
