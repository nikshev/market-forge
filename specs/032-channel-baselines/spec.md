---
traces: [REQ-CHAN-001]
status: draft
---

# Feature Specification: Channel baselines B, C and D

**Feature Branch**: `chan-001-alternative-baselines`

**Created**: 2026-09-09

**Input**: REQ-CHAN-001 — PRD §13.3, §13.4 and §13.5. Extracted because
[[REQ-EXP-001]] compares five channel models and only baseline A existed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A channel a liquidation wick cannot move (Priority: P1)

Huber regression with MAD-derived bands, so one outlier does not drag the
centre.

**Why this priority**: §13.3 states the goal in one line — "reduce sensitivity
to liquidation wicks/outliers". A least-squares centre chases the wick, and the
zones the signal engine reads move with it.

**Acceptance Scenarios**:

1. **Given** a clean series, **When** both baselines fit it, **Then** their centres agree closely.
2. **Given** the same series with one extreme wick, **When** both fit it, **Then** the robust centre moves materially less than the least-squares one.
3. **Given** any fit, **When** the snapshot is read, **Then** it names this model and version, not baseline A's.
4. **Given** the estimators §13.3 lists but this does not build, **When** the baseline is described, **Then** they are named as unbuilt.

---

### User Story 2 - A channel that need not be symmetric (Priority: P1)

Conditional q10, q50 and q90 fitted directly.

**Why this priority**: §13.4's stated purpose — "this supports asymmetric
channels". Baseline A places its bands as residual quantiles around one centre,
so the two sides move together whatever the market does.

**Acceptance Scenarios**:

1. **Given** a series whose upper and lower dispersion differ, **When** the quantile channel fits it, **Then** the distances from centre to each boundary differ.
2. **Given** raw quantile solutions that cross, **When** the fit completes, **Then** the returned boundaries are ordered.
3. **Given** a series with almost no dispersion, **When** the fit completes, **Then** the channel is at least the configured minimum width.
4. **Given** three quantile fits whose slopes disagree, **When** the fit completes, **Then** the disagreement is reported.
5. **Given** a degenerate fit, **When** it is attempted, **Then** it is refused rather than returned.

---

### User Story 3 - A channel that updates one observation at a time (Priority: P1)

A local linear trend filter over level and slope, recursive only.

**Why this priority**: §13.5 forbids the smoother in a single sentence —
"smoother that uses future observations is forbidden for live-compatible
features" — and that is the one mistake a Kalman implementation invites.

**Acceptance Scenarios**:

1. **Given** a series, **When** the filter runs, **Then** each state depends only on observations at or before its own instant.
2. **Given** later observations appended, **When** the filter runs again, **Then** no earlier state changes.
3. **Given** a fit, **When** the snapshot is read, **Then** it reports the state uncertainty.
4. **Given** a series whose innovations grow, **When** the band is derived, **Then** it widens.
5. **Given** the module's source, **When** it is inspected, **Then** it contains no backward pass.

---

### Edge Cases

- What happens when a baseline is given fewer bars than its lookback? It refuses, as baseline A does. A channel fitted on fewer points is a different model wearing the same name.
- What happens when every price in the window is identical? The robust and quantile channels hit their minimum width, and the Kalman band collapses to its observation noise. None reports a channel of zero width, which would make every position on it infinite.
- What happens when the quantile fit's slopes disagree wildly? The channel is still returned, with the disagreement reported in its quality submetrics. Refusing would discard the case a researcher most wants to see.
- What happens to a Kalman filter given one bar? Refused by the lookback rule before the filter runs, so there is no special case for an unset state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every baseline MUST return `ChannelSnapshot`, naming its own model and version.
- **FR-002**: Every baseline MUST filter its own window by `as_of` and use only finalized bars.
- **FR-003**: Every baseline MUST refuse a window shorter than its lookback.
- **FR-004**: Baseline B MUST fit a Huber regression and derive its bands from the MAD of the residuals.
- **FR-005**: Baseline B MUST be measurably less sensitive to a single extreme outlier than baseline A.
- **FR-006**: The §13.3 estimators not built MUST be named as unbuilt in the module.
- **FR-007**: Baseline C MUST fit q10, q50 and q90 conditionally, and MAY produce an asymmetric channel.
- **FR-008**: Baseline C MUST correct quantile crossing.
- **FR-009**: Baseline C MUST enforce a configurable minimum width.
- **FR-010**: Baseline C MUST report slope consistency across the three quantiles.
- **FR-011**: Baseline C MUST refuse a numerically degenerate fit.
- **FR-012**: Baseline D MUST be a recursive local linear trend filter over level and slope.
- **FR-013**: Baseline D MUST contain no backward pass, verified over the source.
- **FR-014**: Baseline D MUST report state uncertainty, and its band MUST derive from innovation variance.
- **FR-015**: No baseline may consult a clock.

### Key Entities

- **Channel snapshot**: as [[REQ-WP-006]] defines it, produced by three more models.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each baseline names its own model and version.
- **SC-002**: Each refuses a short window.
- **SC-003**: One wick moves baseline B's centre less than baseline A's, by a stated margin.
- **SC-004**: Baseline C produces an asymmetric channel on asymmetric data.
- **SC-005**: Crossed raw quantiles come back ordered.
- **SC-006**: The minimum width holds on a flat series.
- **SC-007**: Slope disagreement is reported.
- **SC-008**: Appending later bars changes no earlier Kalman state.
- **SC-009**: The Kalman module contains no backward pass.
- **SC-010**: The Kalman band widens as innovations grow.
- **SC-011**: No baseline references a clock.

## Assumptions

- **No new dependency.** Huber and quantile regression are fitted with NumPy — iteratively reweighted least squares and a linear-programming-free gradient descent respectively — rather than by adding SciPy or statsmodels for two functions.
- **Theil-Sen and RANSAC are not built.** §13.3 lists them as candidates and marks RANSAC experimental "due discontinuous model changes"; naming them as unbuilt is what keeps the module honest about which of §13.3 it is.
- **Quality submetrics are [[REQ-WP-006]]'s**, reused unchanged, so a comparison across models is not a comparison across quality definitions.
