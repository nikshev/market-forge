---
traces: [REQ-EXP-013]
status: draft
---

# Feature Specification: GMDH derivative extrema

**Feature Branch**: `exp-013-gmdh-extrema`

**Created**: 2026-09-09

**Input**: REQ-EXP-013 — four arms, seven metrics, and a rejection rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare all four arms on one set of folds (Priority: P1)

Direct classifier only; GMDH direct turning-point classifier; GMDH forward path
+ derivative roots; ensemble of direct probability + derivative root stability.

**Why this priority**: the derivative route costs four networks per fold, a
promotion gate and a perturbation lattice. Whether that is worth paying for is
only answerable against the cheap arm on the same rows.

**Acceptance Scenarios**:

1. **Given** the four arms, **When** the comparison runs, **Then** each has an entry, in the PRD's order.
2. **Given** any arm, **When** its entry is read, **Then** it carries a Brier score against the no-skill base rate and a calibration curve.
3. **Given** the ensemble, **When** a row has no promoted root, **Then** the classifier half still speaks.
4. **Given** the same folds twice, **When** the comparison runs, **Then** the two reports agree.

---

### User Story 2 - Report the seven metrics the PRD names (Priority: P1)

Root presence rate, root horizon IQR, turn-type agreement, time-to-turn MAE,
extreme-price error, calibration, incremental expectancy after costs.

**Why this priority**: five of the seven are about the derivative route
specifically. A comparison reporting only the shared ones would compare the arms
on the cheap arm's terms.

**Acceptance Scenarios**:

1. **Given** a derivative arm, **When** its entry is read, **Then** all three stability figures are present.
2. **Given** a classifier arm, **When** its entry is read, **Then** the time-to-turn error and the extreme-price error are absent, not zero.
3. **Given** a call whose true forward path never turned, **When** the error is computed, **Then** the call is counted rather than scored as a perfect hit.
4. **Given** any arm but the first, **When** its incremental expectancy is read, **Then** it is that arm's expectancy less the direct classifier's, after costs.
5. **Given** the direct classifier, **When** its incremental expectancy is read, **Then** it is absent — it is not its own increment.

---

### User Story 3 - Reject the derivative method when it does not earn its cost (Priority: P1)

Unstable roots, or no OOS value after costs.

**Why this priority**: this is EXP-013's own last sentence. An experiment that
cannot reject the interesting arm is not an experiment.

**Acceptance Scenarios**:

1. **Given** roots that move outside the horizon under perturbation, **When** the verdict is read, **Then** it is `NO_EDGE` and says the roots are unstable.
2. **Given** a derivative arm that adds nothing over the direct classifier, **When** the verdict is read, **Then** it is `NO_EDGE` and says so.
3. **Given** both failures, **When** the verdict is read, **Then** both are named.
4. **Given** a derivative arm that adds value on stable roots, **When** the verdict is read, **Then** it is `EDGE`.

---

### Edge Cases

- What happens when an arm calls nothing? Its expectancy is absent with the reason, not zero.
- What happens when a called row has no recorded outcome? The comparison refuses: pricing the arm on its other calls would score it on the subset someone happened to resolve.
- What happens when no row produced a root at all? The stability figures are absent and the verdict says there was nothing to assess.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All four arms MUST be compared on the same folds and the same design matrix.
- **FR-002**: Every arm MUST report a Brier score against the no-skill base rate and a calibration curve.
- **FR-003**: The three stability figures MUST be averaged over the rows that produced a root, and both counts MUST be reported.
- **FR-004**: A classifier arm MUST report no time-to-turn error and no extreme-price error.
- **FR-005**: A call whose true forward path never turned MUST be counted, not scored.
- **FR-006**: A call with no promoted root behind it MUST be counted, not silently dropped.
- **FR-007**: The ensemble MUST keep its classifier half where no root was promoted.
- **FR-008**: Incremental expectancy MUST be measured against the direct classifier, after costs.
- **FR-009**: The direct classifier MUST NOT carry an increment of its own.
- **FR-010**: A called row with no recorded outcome MUST be refused.
- **FR-011**: Economic figures MUST refuse to run without a cost model.
- **FR-012**: The call threshold MUST be a required argument and MUST be bounded.
- **FR-013**: The verdict MUST be `NO_EDGE` when the roots are unstable or when no derivative arm adds value, and MUST name every failure rather than the first.
- **FR-014**: The report MUST be deterministic.

### Key Entities

- **Arm report**: one arm's scores, calibration, economics, and — where it makes such a claim — its root and forecast metrics.
- **Root metrics**: the three §13A.12 figures with the denominator they were averaged over.
- **Forecast error**: the two error figures with the three counts that produced them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Four entries, in the PRD's order.
- **SC-002**: Every arm carries a Brier score and a calibration curve.
- **SC-003**: On a fixture where half the paths run straight, the presence rate is 1.0 and the row counts show the halves.
- **SC-004**: The reported horizon IQR matches the production stability function's answer for the fixture's own path.
- **SC-005**: Both classifier arms report absent root and forecast metrics.
- **SC-006**: Compared, without-truth and without-a-root counts sum to the arm's calls.
- **SC-007**: The ensemble calls more rows than the pure derivative arm on a fixture where the classifier is confident without a root.
- **SC-008**: Each increment equals that arm's expectancy less the direct classifier's; the classifier's own is absent.
- **SC-009**: A near-boundary root yields `NO_EDGE` naming instability.
- **SC-010**: An arm that adds nothing yields `NO_EDGE` naming the absent value.
- **SC-011**: Both failures appear in one reason.
- **SC-012**: An interaction target the linear baseline cannot learn yields `EDGE`.
- **SC-013**: A missing outcome on a called row raises; a missing cost model raises.
- **SC-014**: An omitted call threshold raises, and a threshold outside `(0, 1]` raises.
- **SC-015**: Two runs produce equal reports.

## Assumptions

- **The truth is the label-side forward path.** Where it turns is when the turn came, and what it reads there is the extreme price — PRD §24.2's permission, the same one the path targets already use.
- **The promotion gate is [[REQ-WP-019]]'s**, unchanged. This experiment decides how many roots go into one average, not what makes one root acceptable.
- **The exit rule for expectancy is the caller's**, supplied as recorded outcomes.
