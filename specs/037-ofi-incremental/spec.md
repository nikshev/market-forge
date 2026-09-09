---
traces: [REQ-EXP-004]
status: draft
---

# Feature Specification: OFI incremental value

**Feature Branch**: `exp-004-ofi-incremental`

**Created**: 2026-09-09

**Input**: REQ-EXP-004 — five cumulative arms, criteria derived on 2026-09-09.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask what each order-flow family adds (Priority: P1)

Five arms, each containing the last and adding one family, with the difference
between neighbours reported.

**Why this priority**: "incremental value" is a difference. Absolute scores for
five arms leave the reader subtracting, and arms that differ in more than the
family under test make the subtraction meaningless.

**Acceptance Scenarios**:

1. **Given** the five arms, **When** they are read, **Then** each contains the previous arm's families and adds exactly one.
2. **Given** a run, **When** the increments are read, **Then** each names the arm it improves on and the features it added.
3. **Given** a family that carries the signal, **When** its increment is read, **Then** the score moves in the improving direction.
4. **Given** an arm that was not scored, **When** the increment over it is read, **Then** it is absent with a reason, not zero.

---

### User Story 2 - Slice the book finely enough to answer the question (Priority: P1)

L1 imbalance, multi-level imbalance, OFI and wall persistence are four claims,
not one "order flow".

**Why this priority**: [[REQ-US-006]]'s four groups put all of them in one
family, which is the right resolution for that experiment and useless for this
one.

**Acceptance Scenarios**:

1. **Given** EXP-004's taxonomy, **When** an arm names a family outside it, **Then** it is refused.
2. **Given** the default taxonomy, **When** an arm names one of EXP-004's families, **Then** it is refused — the vocabularies stay separate.
3. **Given** the registry, **When** the families are resolved, **Then** each is the set of registered features matching its membership rule.
4. **Given** a fresh process, **When** the families are resolved, **Then** they are complete — not only whatever happened to be imported.

---

### Edge Cases

- What happens when a family has no registered features? Its arm and every arm containing it are reported as not run, and the increments over them are absent. That is the state of every DEX family today.
- What happens when two families resolve to overlapping features? A feature is counted once, and the increment names only what was genuinely added.
- What happens when a feature is added to the book module? It joins the arm whose prefix it matches, without anyone editing this experiment.
- What happens when every arm scores identically? Every increment is zero, which is a finding: the families added nothing on this data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The five arms MUST be EXP-004's, in its order, and cumulative.
- **FR-002**: Each increment MUST name the arm it improves on and the features added.
- **FR-003**: An increment MUST be reported in the direction where better is better, and its sign MUST be stated.
- **FR-004**: An increment involving an unscored arm MUST be absent with a reason.
- **FR-005**: An arm whose family contributes no feature MUST be reported as not run.
- **FR-006**: Every arm MUST be scored on one fold set.
- **FR-007**: EXP-004's families MUST be checked against EXP-004's taxonomy, and the default taxonomy MUST NOT accept them.
- **FR-008**: Family membership MUST be resolved from the feature registry.
- **FR-009**: Resolution MUST be complete in a process that imported nothing else.
- **FR-010**: The scoring MUST be [[REQ-US-006]]'s ablation, not a second path.
- **FR-011**: The report MUST be deterministic.

### Key Entities

- **Arm**: a cumulative feature set.
- **Increment**: what one family added over the arm before it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The arms are cumulative, each adding exactly one family.
- **SC-002**: Every arm appears in the report.
- **SC-003**: Each increment names its baseline and its added features.
- **SC-004**: A family carrying the signal improves the score, in the stated direction.
- **SC-005**: An increment over an unscored arm is absent with a reason.
- **SC-006**: An empty family's arm is not run.
- **SC-007**: All arms share one fold set.
- **SC-008**: Each taxonomy refuses the other's families.
- **SC-009**: The families resolve from the registry, non-empty.
- **SC-010**: They resolve completely in a fresh process.
- **SC-011**: Two runs produce equal reports.

## Assumptions

- **The channel features are registered.** They were not, and every arm here rests on a channel baseline; registering them closes a PRD §19 gap that predates this experiment.
- **The rows are supplied and certified**, as [[REQ-US-007]] requires of anything that fits a model.
