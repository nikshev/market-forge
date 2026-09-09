---
traces: [REQ-EXP-006]
status: draft
---

# Feature Specification: Derivatives context

**Feature Branch**: `exp-006-derivatives-context`

**Created**: 2026-09-09

**Input**: REQ-EXP-006 — conditional outcomes by funding z-score, OI change,
liquidation imbalance and basis. Criteria derived on 2026-09-09.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Split the outcomes by the state they happened in (Priority: P1)

Four variables, declared buckets, counts and economics for each.

**Why this priority**: the conditional is the experiment. Buckets chosen from
the sample would move with it, and two windows would bucket the same funding
reading differently.

**Acceptance Scenarios**:

1. **Given** the four variables, **When** the study runs, **Then** each has an entry.
2. **Given** declared edges, **When** the buckets are read, **Then** they are those edges and each carries its count.
3. **Given** a bucket below the configured minimum, **When** it is read, **Then** it carries its count and no score.
4. **Given** setups that did well at one extreme and badly at the other, **When** the conditional is read, **Then** it shows the difference.

---

### User Story 2 - Never render an absence as a flat conditional (Priority: P1)

A variable no observation carries is unavailable, not one bucket holding
everything.

**Why this priority**: rendered as a single bucket, "no data" and "no
relationship" look identical, and only one of them is a finding about the
market.

**Acceptance Scenarios**:

1. **Given** a variable absent from every observation, **When** the study runs, **Then** it is reported unavailable with the reason and no buckets.
2. **Given** that same study, **When** the other variables are read, **Then** they are unaffected.

---

### User Story 3 - Say whether the answer forecasts or explains (Priority: P1)

Every report states whether the state was read at signal time or around the
outcome.

**Why this priority**: EXP-014 names the trap for the whole family — "repeat
point-in-time as a predictive experiment to avoid confusing contemporaneous
explanation with forecast value". Only one of the two is tradeable.

**Acceptance Scenarios**:

1. **Given** a point-in-time study, **When** its note is read, **Then** it says the conditionals are predictive.
2. **Given** a contemporaneous one, **When** its note is read, **Then** it says they explain rather than forecast.
3. **Given** the study's signature, **When** it is inspected, **Then** the flag has no default.

---

### Edge Cases

- What happens when every setup falls in one bucket? The others report zero setups and no score, which says the edges did not divide this sample.
- What happens when a bucket has setups but none resolved? It carries its count and the reason, from the economics layer's own refusal.
- What happens when two variables disagree? Both are reported. The study conditions on one variable at a time; a joint conditional is a different and much hungrier experiment.
- What happens when the caller supplies edges for one variable only? The rest keep their declared defaults, and every report carries the edges it used.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All four variables MUST be reported.
- **FR-002**: Buckets MUST come from declared edges, never from the sample's own quantiles.
- **FR-003**: Every bucket MUST carry its setup count.
- **FR-004**: A bucket below the configured minimum MUST NOT be scored.
- **FR-005**: A variable no observation carries MUST be reported unavailable with the reason, and MUST NOT become one bucket.
- **FR-006**: Every bucket MUST be scored under the same cost model.
- **FR-007**: Ambiguous outcomes MUST be excluded and counted.
- **FR-008**: The report MUST state whether it is point-in-time or contemporaneous, and the flag MUST have no default.
- **FR-009**: The study MUST be refused without a cost model.
- **FR-010**: The report MUST be deterministic.

### Key Entities

- **Observation**: the derivatives state a setup was seen in, and its outcome.
- **Bucket**: one band of one variable, its count, and its economics or the reason it has none.
- **Report**: every variable's conditional, the costs, and what kind of study it was.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Four entries, one per variable.
- **SC-002**: Buckets match the declared edges and their counts sum to the sample.
- **SC-003**: A thin bucket is reported unscored.
- **SC-004**: A real conditional difference is visible in the economics.
- **SC-005**: A variable with no data is unavailable and the others still run.
- **SC-006**: Both study kinds label themselves; the flag has no default.
- **SC-007**: Ambiguous outcomes are excluded and counted.
- **SC-008**: Every bucket carries the same costs, and raising them lowers every bucket.
- **SC-009**: No cost model refuses.
- **SC-010**: Two runs produce equal reports.

## Assumptions

- **Outcomes and states are supplied.** Reading a funding z-score at signal time is pipeline work; this study conditions on what it is given.
- **One variable at a time.** A joint conditional over four variables needs far more setups than any of these buckets will hold.
- **The edges are research defaults.** They decide which bucket a reading joins, and PRD §13.11's warning applies to them.
