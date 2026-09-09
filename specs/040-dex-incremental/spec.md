---
traces: [REQ-EXP-007]
status: draft
---

# Feature Specification: DEX incremental value

**Feature Branch**: `exp-007-dex-incremental`

**Created**: 2026-09-09

**Input**: REQ-EXP-007 — five cumulative arms for ETH. Criteria derived on
2026-09-09.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask what the DEX view adds, one family at a time (Priority: P1)

CEX only, then divergence, depth asymmetry, swap imbalance, LP liquidity.

**Why this priority**: the DEX families are expensive to collect, and the
question is which of them is worth collecting.

**Acceptance Scenarios**:

1. **Given** the five arms, **When** they are read, **Then** each contains the previous one and adds exactly one family.
2. **Given** rows carrying every family, **When** the ablation runs, **Then** every arm is scored and each increment names what it added.
3. **Given** a family that carries the signal, **When** its increment is read, **Then** it moves in the improving direction.
4. **Given** an arm naming a family outside this taxonomy, **When** it is built, **Then** it is refused.

---

### User Story 2 - Report the state of the pipeline honestly (Priority: P1)

Every DEX family resolves to nothing today, so four of five arms report as not
run.

**Why this priority**: an arm scored on features it does not have reports the
absence of data as the absence of value — and this experiment is the one where
that mistake is most tempting, because the DEX work exists and only the
registration does not.

**Acceptance Scenarios**:

1. **Given** the registry as it is, **When** the families are resolved, **Then** every DEX one is empty and the CEX one is not.
2. **Given** that resolution, **When** the ablation runs, **Then** the four DEX arms report as not run with reasons and the CEX arm is scored.
3. **Given** the registration later happening, **When** the test suite runs, **Then** the expectation fails and says so.

---

### User Story 3 - Say which pool the answer is about (Priority: P2)

The report names its instrument.

**Why this priority**: EXP-007 names ETH, and a DEX result is about a pool. A
report that did not say which would be a result about nothing in particular.

**Acceptance Scenarios**:

1. **Given** an instrument, **When** the report is read, **Then** it carries it.
2. **Given** no instrument, **When** the ablation is requested, **Then** it is refused.

---

### Edge Cases

- What happens when only some DEX families are registered? Those arms run and the rest report not run, and the increments across a gap are absent rather than zero.
- What happens when the caller supplies the features directly? The arms run on what was supplied. The registry is the default, not the only source.
- What happens when the CEX family is empty too? Every arm is not run, and the report is a statement about the dataset rather than about the DEX.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The five arms MUST be EXP-007's, in its order, and cumulative.
- **FR-002**: An arm whose family contributes no feature MUST be reported as not run.
- **FR-003**: Each increment MUST name the arm it improves on and the features added.
- **FR-004**: An increment involving an unscored arm MUST be absent, not zero.
- **FR-005**: EXP-007's families MUST be checked against EXP-007's taxonomy.
- **FR-006**: Family membership MUST be resolved from the feature registry by declared prefixes.
- **FR-007**: The divergence family MUST NOT match the perp-spot basis, which is a CEX derivatives feature.
- **FR-008**: The report MUST carry its instrument, and the instrument MUST be required.
- **FR-009**: The report MUST be deterministic.

### Key Entities

- **Arm**: a cumulative feature set.
- **Report**: the ablation, its increments, and the instrument.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The arms are cumulative, each adding one family.
- **SC-002**: With features supplied, every arm scores and the increments name what they added.
- **SC-003**: A family carrying the signal improves the score in the stated direction.
- **SC-004**: With the registry as it is, every DEX family is empty and the four arms report not run.
- **SC-005**: The divergence family does not pick up `basis_bps`.
- **SC-006**: The instrument is reported, and required.
- **SC-007**: A family outside the taxonomy refuses.
- **SC-008**: Two runs produce equal reports.

## Assumptions

- **The DEX features are unregistered, not unbuilt.** [[REQ-WP-015]] and
  [[REQ-WP-016]] compute divergence, depth asymmetry and swap imbalance; PRD §19
  registration for them is separate work, and until it happens this report says
  so.
- **The cumulative machinery is [[REQ-EXP-004]]'s**, shared rather than copied,
  so both experiments' increments mean the same thing.
