---
traces: [REQ-EXP-012]
status: draft
---

# Feature Specification: Causal derivative turning points

**Feature Branch**: `exp-012-derivative-turning`

**Created**: 2026-09-09

**Input**: REQ-EXP-012 — four causal slope estimators, four horizons, centred filters as labels only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare the causal slope estimators the PRD names (Priority: P1)

Raw trailing return sign change, causal local polynomial order 2, causal local
polynomial order 3, Kalman filtered slope.

**Why this priority**: the question EXP-012 asks is which of these sees a turn
coming. A comparison missing one of them answers a different question.

**Acceptance Scenarios**:

1. **Given** the four candidates, **When** the comparison runs, **Then** each has an entry.
2. **Given** a candidate that calls nothing, **When** its entry is read, **Then** its precision is absent rather than zero.
3. **Given** a noisy series, **When** the raw and the fitted candidates are compared, **Then** the raw one calls more turns.
4. **Given** the same bars twice, **When** the comparison runs, **Then** the two reports are equal.

---

### User Story 2 - Refuse a centred filter as a live candidate (Priority: P1)

A centred filter is the best turning-point detector here, and it is disqualified
by construction.

**Why this priority**: this is the line EXP-012 ends on and the one this module
could most easily cross. A centred filter's answer at bar `t` changes when bar
`t + 1` arrives, so it can be measured and never traded.

**Acceptance Scenarios**:

1. **Given** a candidate that declares itself centred, **When** the comparison runs, **Then** it is refused by name.
2. **Given** that refusal, **When** its cause is read, **Then** it came from the production causality guard, not a copy of its logic.
3. **Given** the labeller, **When** its declaration is read, **Then** it says it is centred.
4. **Given** a report, **When** it is read, **Then** it says the labels came from a centred filter that cannot run live.

---

### User Story 3 - Report precision at all four horizons (Priority: P1)

3, 6, 12 and 24 bars.

**Why this priority**: how far ahead a call counts is the whole content of the
comparison. Four numbers that cannot differ are one number printed four times.

**Acceptance Scenarios**:

1. **Given** any candidate, **When** its entry is read, **Then** it carries one measurement per horizon, in the PRD's order.
2. **Given** a call outside the tolerance but inside a longer horizon, **When** precision is read, **Then** it is zero at the short horizons and one at the long ones.
3. **Given** a candidate's four measurements, **When** they are compared, **Then** a longer horizon never lowers precision.

---

### Edge Cases

- What happens when a candidate calls nothing at all? Its precision is absent at every horizon: precision over no calls is not zero, and a silent method is not a wrong one.
- What happens when the series has no labelled turn? Every call is a miss — reported as zero precision, which is the true reading, not a missing one.
- What happens with a fitted slope over the first few bars, before a window exists? It reports zero, which makes no call, rather than a fit over data it does not have.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All four causal candidates MUST be compared.
- **FR-002**: A candidate that declares itself centred MUST be refused, by name.
- **FR-003**: The refusal MUST come from the production causality guard.
- **FR-004**: The labels MUST be made by a centred filter that declares itself centred.
- **FR-005**: The report MUST state that its labels came from a centred filter that cannot run live.
- **FR-006**: Precision MUST be reported at horizons 3, 6, 12 and 24 bars.
- **FR-007**: A local polynomial's slope MUST be read at the right edge of its window.
- **FR-008**: Precision over no calls MUST be absent, not zero.
- **FR-009**: A longer horizon MUST NOT lower precision.
- **FR-010**: A call MUST be a sign change in the estimated slope, not every bar.
- **FR-011**: The report MUST be deterministic.

### Key Entities

- **Method**: one candidate estimator, its causality declaration, and its slopes.
- **Horizon precision**: one horizon's calls and hits for one method.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Four entries, one per candidate.
- **SC-002**: A centred candidate is refused by name.
- **SC-003**: The refusal's cause is the production guard's own exception.
- **SC-004**: The labeller declares `centered` true.
- **SC-005**: The report names both the centred filter and its inability to run live.
- **SC-006**: Four horizons per entry, in the PRD's order.
- **SC-007**: A fit past a peak is negative at the right edge and positive at the centre; the reported number is the first.
- **SC-008**: A silent method's precision is absent at every horizon.
- **SC-009**: A call eight bars early scores zero at 3 and 6 and one at 12 and 24.
- **SC-010**: Every entry's precisions are non-decreasing in the horizon.
- **SC-011**: A raw sign change calls more turns than a fitted slope on a noisy series.
- **SC-012**: Two runs produce equal reports.

## Assumptions

- **The Savitzky-Golay-equivalent variant is absent by design.** EXP-012 lists it "if retained": its one-sided form is the causal local polynomial already here, and its centred form is a label maker, not a candidate.
- **Precision, not recall.** A method that calls every bar a turn has perfect recall and no information, and precision is what a reader of an alert experiences.
- **The tolerance is a research default** — two bars — and it decides what "found it" means.
