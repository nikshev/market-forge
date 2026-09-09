---
traces: [REQ-EXP-016]
status: draft
---

# Feature Specification: Multi-scale extrema

**Feature Branch**: `exp-016-multi-scale`

**Created**: 2026-09-09

**Input**: REQ-EXP-016 — three nesting rules, incremental value, not visual appeal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evaluate all three nesting rules (Priority: P1)

A 5m candidate inside the 15m zone; a 15m candidate aligned with the 1h slope;
directional-change thresholds at multiple scales.

**Why this priority**: each is a different claim about what a higher timeframe
adds, and the third is the conjunction of the first two rather than a looser
version of either.

**Acceptance Scenarios**:

1. **Given** the three rules, **When** the evaluation runs, **Then** each has a result, in the PRD's order.
2. **Given** a rule outside the three, **When** it is requested, **Then** it is refused.
3. **Given** a candidate inside the zone but conflicted with the slope, **When** the multi-scale rule reads it, **Then** it is rejected — and likewise for aligned but outside.
4. **Given** a candidate exactly at the edge of the zone, **When** the zone rule reads it, **Then** it is inside.

---

### User Story 2 - Measure incremental value, not visual appeal (Priority: P1)

Per trade and in total, against the same candidates without the rule.

**Why this priority**: EXP-016's own last sentence. A chart of the candidates
that survived three timeframes agreeing looks better than a chart of all of
them, because the trades the filter removed are not on the page.

**Acceptance Scenarios**:

1. **Given** any rule, **When** its result is read, **Then** it carries the change in the average trade, the change in the total, and how much it kept.
2. **Given** a rule that lifts the average and loses the total, **When** it is read, **Then** it is named as such and listed.
3. **Given** a rule that earns its selectivity, **When** it is read, **Then** it improves both.
4. **Given** a rule that helps neither way, **When** it is read, **Then** it says so.
5. **Given** a rule that kept nothing, **When** its expectancy is read, **Then** it is absent rather than zero.
6. **Given** the rejected candidates, **When** they are read, **Then** they are priced too.

---

### User Story 3 - Read only a higher timeframe that had closed (Priority: P1)

**Why this priority**: a 5-minute candidate sits inside a 15-minute bar that has
not finished. That bar's zone is partly made of what happened after the
candidate, and reading it improves every number in the experiment.

**Acceptance Scenarios**:

1. **Given** a candidate and the frame containing it, **When** context is resolved, **Then** the last *closed* frame is used.
2. **Given** frames out of closing order, **When** context is resolved, **Then** it is refused.
3. **Given** a candidate before any frame has closed, **When** the evaluation runs, **Then** it is excluded from every arm and counted.

---

### Edge Cases

- What happens when a rule keeps every candidate? Its selectivity is one and its deltas are zero — it selected nothing.
- What happens when no candidate resolves? The set has no expectancy, with the reason.
- What happens to a candidate whose direction is neither long nor short? Refused at construction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All three rules MUST be evaluated, in the PRD's order; an unknown rule MUST be refused.
- **FR-002**: The multi-scale rule MUST require both scales.
- **FR-003**: The zone MUST include its own edges.
- **FR-004**: Alignment MUST depend on the candidate's direction and the higher slope's sign.
- **FR-005**: Each rule MUST report the change in the average trade and the change in the total, plus its selectivity.
- **FR-006**: The rejected candidates MUST be priced, not discarded.
- **FR-007**: Only a higher-timeframe frame that had closed at the candidate's time MUST be visible.
- **FR-008**: Frames out of closing order MUST be refused.
- **FR-009**: A candidate without context MUST be excluded from every arm and counted.
- **FR-010**: A set that kept nothing MUST have absent economics, not zero.
- **FR-011**: The improvement floor MUST be a required, positive argument and MUST decide the per-trade reading.
- **FR-012**: The reading MUST name the case where the average improves and the total falls.
- **FR-013**: The report MUST be deterministic.

### Key Entities

- **Higher frame**: one completed higher-timeframe bar, and when it closed.
- **Set economics**: one set of candidates priced after costs, per trade and in total.
- **Rule result**: base, kept and rejected sets, the two deltas, and the reading.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Three results in the PRD's order; an unknown rule raises.
- **SC-002**: A candidate that satisfies one scale only fails the multi-scale rule, both ways round.
- **SC-003**: A candidate at either edge of the zone is inside it.
- **SC-004**: Every result carries both deltas and its selectivity.
- **SC-005**: A selective rule that lifts the average and loses the total is named and listed.
- **SC-006**: A rule that earns its selectivity improves both.
- **SC-007**: A rule against an inverted fixture improves neither.
- **SC-008**: Rejected plus kept equals the base.
- **SC-009**: The frame used is the last closed one, not the one containing the candidate.
- **SC-010**: Out-of-order frames raise.
- **SC-011**: A candidate before any frame closed is counted and left out of the base.
- **SC-012**: A rule that kept nothing has absent expectancy, absent total, absent deltas and reads as unmeasured.
- **SC-013**: An omitted improvement floor raises; a floor of zero raises; the same rule reads differently at two floors.
- **SC-014**: A direction that is neither long nor short raises.
- **SC-015**: Two runs produce equal reports.

## Assumptions

- **The candidates and their outcomes are supplied.** Detecting them is [[REQ-WP-019]]'s job and pricing them is [[REQ-BT-001]]'s.
- **The higher-timeframe context is supplied as completed frames.** Building them from bars is the channel layer's job.
- **The floor guards the per-trade number only.** The total is the book's own outcome over the same candidates; holding it to a per-trade floor would give one number two meanings.
