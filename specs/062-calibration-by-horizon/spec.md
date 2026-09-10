---
traces: [REQ-WP-023]
status: draft
---

# Feature Specification: Calibration per horizon

**Feature Branch**: `wp-023-calibration-by-horizon`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-023 — PRD §23.5A's three horizon-conditioned classes, and Phase 7's last deliverable.

## Context

PRD §23.5A conditions all three Target E classes on an explicit horizon `H`.
`calibration()` reports one reliability curve over every prediction it is handed
and nothing slices it.

A model's reliability is not constant across horizons: five bars ahead is nearly
the present, fifty is a different question about a different market. Pooled, a
model well calibrated at short horizons and badly at long ones reports an
acceptable number — the average is dragged toward whichever horizon supplied the
most rows, which is a fact about the dataset rather than about the model. The
failure the pooled figure hides is the one that matters, because a forecast is
acted on at one horizon and not at the average of several.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliability is reported per horizon (Priority: P1)

A reader sees how well calibrated the model is at each horizon it was asked
about, separately.

**Acceptance Scenarios**:

1. **Given** predictions over rows with two horizons, **When** calibration is reported, **Then** there is one curve per horizon.
2. **Given** a model calibrated at one horizon and not at another, **When** calibration is reported, **Then** the two curves differ and neither is the average.
3. **Given** the pooled figure beside them, **When** the slices disagree, **Then** the pooled figure is still reported and is not the only thing reported.

---

### User Story 2 - A horizon that cannot speak says so (Priority: P1)

A horizon with too few observations is reported as unmeasured, with its count.

**Why this priority**: The whole point of slicing is to stop an average speaking
for a slice. A slice with three rows that reports a curve has borrowed the
average's voice in a new place.

**Acceptance Scenarios**:

1. **Given** a horizon with fewer observations than the caller's minimum, **When** calibration is reported, **Then** it is marked unmeasured with its count rather than given a curve.
2. **Given** an unmeasured horizon, **When** a reader looks for its reliability, **Then** absent and poor are distinguishable.
3. **Given** the minimum, **When** it is chosen, **Then** it is the caller's and not a constant inside the reporter.

---

### User Story 3 - The horizon is the row's own (Priority: P2)

A row's horizon comes from its label, not from an argument.

**Acceptance Scenarios**:

1. **Given** rows whose labels carry different horizons, **When** calibration is reported, **Then** the grouping follows the labels.
2. **Given** a caller who believes the horizons are uniform and is wrong, **When** calibration is reported, **Then** the report shows the horizons that were actually present.

### Edge Cases

- **One horizon only.** One slice, and the pooled figure equals it — which is a fact worth being able to see rather than a reason to omit either.
- **Predictions and rows of different lengths.** Refused: a report over a misaligned pair would be arithmetic on unrelated numbers.
- **No rows at all.** Refused, for the reason `calibration()` already refuses it: calibration over no predictions is not zero error.
- **A target that never occurs at one horizon.** Its slice has observations but no positive outcomes; that is a measurable calibration, not an unmeasured one, and the difference must survive.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Calibration MUST be reported per horizon.
- **FR-002**: A horizon's observations MUST be counted and reported.
- **FR-003**: A horizon with fewer observations than the caller's minimum MUST be reported as unmeasured, with its count, and MUST NOT be given a curve.
- **FR-004**: The minimum MUST be supplied by the caller.
- **FR-005**: A horizon MUST be derived from each row's own label.
- **FR-006**: The pooled figure MUST be reported beside the slices, never instead of them.
- **FR-007**: Mismatched lengths and empty input MUST be refused.
- **FR-008**: `calibration()` MUST keep returning what it returns today.

### Key Entities

- **Horizon slice**: one horizon, its observation count, and either a reliability curve or the reason there is none.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Rows spanning N horizons produce N slices.
- **SC-002**: A slice's observation count equals the rows at that horizon.
- **SC-003**: A slice below the minimum carries no curve and states its count.
- **SC-004**: A model calibrated at one horizon and not another yields curves that differ, and the pooled figure equals neither.
- **SC-005**: Changing the caller's minimum changes which slices are unmeasured and nothing else.
- **SC-006**: Every existing `calibration()` result is unchanged.

## Assumptions

- **Horizons are grouped exactly, not bucketed.** Labels are built with a stated `H`, so rows share exact horizons; inventing bands would add a second arbitrary choice on top of the minimum.
- **The minimum is configuration.** Principle X, and PRD §23.8 gives no number — so a constant inside the reporter would be a threshold nobody could change.
- **Producing the forecasts is out of scope.** §23.5B and §12's forecast record are separate work.
