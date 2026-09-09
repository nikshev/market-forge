---
traces: [REQ-EXP-009]
status: draft
---

# Feature Specification: Forecast corridor calibration

**Feature Branch**: `exp-009-corridor-calibration`

**Created**: 2026-09-09

**Input**: REQ-EXP-009 — three corridor constructions, and one metric: "target
coverage with narrowest stable interval". PRD §13.7 and §13.8.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure what each corridor actually covers (Priority: P1)

Empirical residual quantile, parametric band, conformal-adjusted interval — each
fitted forward and scored on what followed.

**Why this priority**: an 80% corridor that contains 62% of what follows is not
a narrow corridor, it is a wrong one, and nothing downstream can tell.

**Acceptance Scenarios**:

1. **Given** the three methods, **When** the comparison runs, **Then** each has a coverage and a width.
2. **Given** a channel with a slope, **When** the corridor is projected, **Then** it follows the slope rather than sitting flat.
3. **Given** a series too short, **When** the comparison runs, **Then** it is refused rather than measured over a handful of fits.
4. **Given** a target outside PRD §13.8's levels, **When** it is requested, **Then** it is refused.

---

### User Story 2 - Pick the narrowest that keeps its promise (Priority: P1)

Stable means every fold, not the average.

**Why this priority**: the metric says "narrowest stable", and both words are
load-bearing. A corridor covering 95% in one window and 65% in another averages
to 80% and is useless in both.

**Acceptance Scenarios**:

1. **Given** a narrow corridor that misses the target and a wider one that holds it, **When** a winner is picked, **Then** it is the wider one.
2. **Given** a corridor whose folds swing around the target, **When** stability is judged, **Then** it is not stable.
3. **Given** no method holding the target, **When** a winner is picked, **Then** there is none, and the narrowest failure is not offered instead.
4. **Given** two stable corridors of equal width, **When** one is picked, **Then** the choice is by a declared key.

---

### User Story 3 - Let the conformal method adapt without cheating (Priority: P1)

Its half-width comes from recent errors — and never from the error it is about
to be judged on.

**Why this priority**: a corridor calibrated on its own outcome widens exactly
when it needs to, and reports coverage no live system could achieve.

**Acceptance Scenarios**:

1. **Given** a large error, **When** the corridor at that instant is read, **Then** its width has not yet reacted.
2. **Given** the instant after, **When** its width is read, **Then** it has.
3. **Given** a series whose volatility changes, **When** the widths are compared, **Then** the conformal one differs from the channel's own.

---

### Edge Cases

- What happens before enough errors have accumulated? The conformal corridor falls back to the empirical one and says nothing false — it is not yet calibrated, and a quantile over three errors is not a quantile.
- What happens when every method holds the target? The narrowest wins, which is the metric working rather than a tie.
- What happens when coverage is measured over one fold? It is reported as one fold; the stability question needs more, and the report shows how many it had.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All three methods MUST be measured on the same fits, horizon and series.
- **FR-002**: The forecast centre MUST be projected along the channel's slope.
- **FR-003**: Coverage MUST be reported per chronological fold.
- **FR-004**: Stability MUST require the target on every fold.
- **FR-005**: The winner MUST be the narrowest stable method, with ties broken by a declared key.
- **FR-006**: With nothing stable there MUST be no winner, and the narrowest failure MUST NOT be substituted.
- **FR-007**: The target coverage MUST be one of PRD §13.8's levels.
- **FR-008**: The conformal half-width MUST come only from errors already observed.
- **FR-009**: A series yielding too few measurements MUST be refused.
- **FR-010**: The report MUST be deterministic.

### Key Entities

- **Measurement**: one instant's widths and hits.
- **Method result**: coverage by fold, mean width, observation count.
- **Report**: every method, the target, and the winner or the reason there is none.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Three methods measured, each with observations.
- **SC-002**: A trending series does not lose coverage, showing the centre is projected.
- **SC-003**: Coverage is reported per fold and the folds differ on a regime-change series.
- **SC-004**: A swinging corridor is unstable though its mean meets the target.
- **SC-005**: The narrowest stable method wins, not the narrowest.
- **SC-006**: Nothing stable yields no winner and a stated reason.
- **SC-007**: Equal widths break by name.
- **SC-008**: An unsupported target refuses; a short series refuses.
- **SC-009**: The conformal width does not react to the error it is judged on.
- **SC-010**: Two runs produce equal reports.

## Assumptions

- **The three methods are the PRD's**, and the conformal one is §13.8's rolling residual calibration rather than a full adaptive conformal scheme, which §13.8 marks optional.
- **The channel model is held fixed.** EXP-009 varies the interval construction; [[REQ-EXP-001]] varies the model.
