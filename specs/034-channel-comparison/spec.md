---
traces: [REQ-EXP-001]
status: draft
---

# Feature Specification: Channel model comparison

**Feature Branch**: `exp-001-channel-comparison`

**Created**: 2026-09-09

**Input**: REQ-EXP-001 — PRD's EXP-001. Five channel models, seven metrics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare all five models on one series (Priority: P1)

Every model EXP-001 names, over the same bars, reporting the same seven metrics.

**Why this priority**: the experiment is the comparison. A report missing a
model is a comparison whose winner might not have been in it.

**Acceptance Scenarios**:

1. **Given** the five models, **When** the comparison runs, **Then** each has an entry.
2. **Given** one bar series, **When** the models are compared, **Then** every model saw the same bars and the same split.
3. **Given** a model that cannot fit the series, **When** the comparison runs, **Then** it is reported as unfitted with the reason, and the others still run.
4. **Given** one input, **When** the comparison runs twice, **Then** the reports are equal.

---

### User Story 2 - Measure what a channel is for (Priority: P1)

Coverage, boundary stability, false perfect touches, slope and width stability,
and cost.

**Why this priority**: EXP-001 lists them, and each answers a different failure.
A channel can be stable and useless, or well-covered and jittery.

**Acceptance Scenarios**:

1. **Given** a fitted model, **When** coverage is measured, **Then** it is the share of the next H closes that fell inside the channel fitted before them.
2. **Given** a model whose bands are wider, **When** coverage is compared, **Then** it is higher — the measure responds to the thing it measures.
3. **Given** consecutive fits, **When** slope and width stability are measured, **Then** they are the dispersion of those values across the fits.
4. **Given** consecutive fits, **When** boundary stability is measured, **Then** it is the share of bars whose boundary classification survived the next refit.
5. **Given** a bar that the later channel calls a perfect touch and the channel of the time did not, **When** false perfect touches are counted, **Then** that bar is counted.
6. **Given** the models, **When** cost is reported, **Then** it is a deterministic figure, equal across two runs.

---

### User Story 3 - Say what the choice is worth out of sample (Priority: P1)

Expectancy in R, after costs, on a locked-out final segment.

**Why this priority**: EXP-001's seventh metric, and the only one that says
whether a better-looking channel is a better channel. PRD §41 rule 10 keeps the
test segment untouched.

**Acceptance Scenarios**:

1. **Given** a bar series and a split, **When** expectancy is measured, **Then** it is computed only on the out-of-sample segment.
2. **Given** the models, **When** expectancy is measured, **Then** every one uses the same rejection rule, the same fills and the same costs.
3. **Given** no cost model, **When** the comparison is asked for expectancy, **Then** it is refused.
4. **Given** a model producing no confirmed setups out of sample, **When** its expectancy is read, **Then** it is absent with a reason, not zero.

---

### Edge Cases

- What happens when a model produces one confirmed setup? Its expectancy is reported over one trade and the trade count is beside it, so nobody reads a single sample as a result.
- What happens when the series is shorter than the longest lookback? The comparison refuses: models fitted on different amounts of history are not being compared to each other.
- What happens when two models tie on every metric? Both are reported and neither is declared the winner — the report ranks, it does not choose.
- What happens when a model's channel is degenerate (zero width)? Coverage is undefined for it and reported as absent; the model is not silently credited with perfect or zero coverage.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All five of EXP-001's models MUST appear in the report.
- **FR-002**: Every model MUST be measured over the same bars, split and horizon.
- **FR-003**: A model that cannot fit MUST be reported with the reason, and MUST NOT stop the others.
- **FR-004**: Coverage MUST be the share of the next H closes inside the channel fitted at the instant before them.
- **FR-005**: Slope and width stability MUST be the dispersion of those values across consecutive fits.
- **FR-006**: Boundary stability MUST be the share of bars whose boundary classification survives the next refit.
- **FR-007**: A false perfect touch MUST be a bar the later channel calls a boundary touch and the channel of the time did not.
- **FR-008**: Computational cost MUST be reported as a deterministic figure.
- **FR-009**: Expectancy MUST be computed only on the out-of-sample segment.
- **FR-010**: Every model MUST use the same rejection rule, fill model and cost model.
- **FR-011**: Expectancy MUST be refused without a cost model.
- **FR-012**: A model with no out-of-sample setups MUST report absent expectancy with a reason, never zero.
- **FR-013**: The report MUST be deterministic.
- **FR-014**: The comparison MUST refuse a series too short for the longest lookback.

### Key Entities

- **Model entry**: one model's seven metrics, or the reason it has none.
- **Comparison report**: every entry, the split, and the settings every model shared.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Five entries, one per model.
- **SC-002**: A wider-banded model scores higher coverage.
- **SC-003**: A jittery model scores worse slope and width stability than a steady one.
- **SC-004**: A constructed repaint produces a false perfect touch.
- **SC-005**: Cost is equal across two runs.
- **SC-006**: Expectancy uses only the out-of-sample segment, verified by changing the in-sample bars and seeing it unchanged.
- **SC-007**: Expectancy without costs refuses.
- **SC-008**: A model with no setups reports absent expectancy with a reason.
- **SC-009**: Two runs produce equal reports.
- **SC-010**: A short series refuses.

## Assumptions

- **The rejection rule is fixed and declared.** EXP-001 compares channel models, so the exit rule is held constant across them; which rule it is matters less than that it is the same one.
- **Computational cost is a deterministic operation count, not wall clock.** A wall-clock figure changes between runs, and a report that cannot be compared to itself cannot be compared to another.
- **Coverage is measured forward from each fit.** That is an evaluation, not a feature: the channel is fitted on data up to `t` and scored on what followed, which is the only way to measure coverage at all.
