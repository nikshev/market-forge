---
traces: [REQ-WP-006]
status: draft
---

# Feature Specification: Channel baseline

**Feature Branch**: `wp-006-channel-baseline`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-006 — rolling OLS log price; residual quantile bands; normalized slope; quality score; append-only storage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fit a channel that cannot see the future (Priority: P1)

Given bars up to a moment, the model produces a channel snapshot describing the
price structure as it stood at that moment — and provably could not have used
anything later.

**Why this priority**: PRD §13.1 states the hard invariant
`source_max_event_time <= as_of`, and §2.1 identifies repainting as the critical
risk the entire product exists to avoid. A channel that peeks is worse than no
channel, because it looks accurate in a backtest and fails live.

**Independent Test**: Fit on a bar history, then append later bars and refit at
the original `as_of`. The snapshot is identical.

**Acceptance Scenarios**:

1. **Given** a bar history, **When** a channel is fitted at `as_of`, **Then** the snapshot's `source_max_event_time` is at or before `as_of`.
2. **Given** a snapshot fitted at `as_of`, **When** later bars are appended and the fit repeats at the same `as_of`, **Then** the snapshot is identical field for field.
3. **Given** bars after `as_of` in the input, **When** the fit runs, **Then** they are excluded rather than silently used.
4. **Given** fewer bars than the lookback requires, **When** the fit is attempted, **Then** it refuses rather than fitting on what it has.

---

### User Story 2 - Describe the channel in usable terms (Priority: P1)

The snapshot carries the centre, the boundaries, a slope comparable across
symbols, and a width — enough for a scanner to rank markets and for a state
machine to decide where price sits.

**Why this priority**: Equal to US1. A correct channel nobody can act on is not
useful, and PRD §13.10's position coordinate is built directly from these
fields.

**Independent Test**: Fit on a synthetic series with a known slope and known
noise; the reported values match the construction.

**Acceptance Scenarios**:

1. **Given** bars generated from a known log-linear trend, **When** the channel is fitted, **Then** the recovered slope matches the constructed one within the noise.
2. **Given** a fitted channel, **When** the bands are computed, **Then** they come from empirical residual quantiles at the configured levels, defaulting to 0.10 and 0.90.
3. **Given** two symbols at very different price levels but identical shape, **When** both are fitted, **Then** their normalized slopes are equal.
4. **Given** a fitted channel, **When** the centre is read, **Then** it is the exponential of the fitted log-price line, not a mean of prices.

---

### User Story 3 - Judge how much to trust the channel (Priority: P2)

The snapshot carries a quality score in `[0,1]` and says which submetrics
produced it, so a consumer can tell a well-formed channel from a fitted line
through noise.

**Why this priority**: PRD §1.2 makes the product's whole hypothesis conditional
on channel quality — the edge is in `P(success | channel_state, ...)`, not in
the channel alone. Below US1 and US2 because a wrong score is recoverable while
a peeking channel is not.

**Independent Test**: Fit on a clean trending series and on pure noise; the
former scores materially higher.

**Acceptance Scenarios**:

1. **Given** a series that respects its channel, **When** quality is scored, **Then** coverage is near the configured band width.
2. **Given** pure noise, **When** quality is scored, **Then** the score is materially lower than for a clean trend.
3. **Given** any snapshot, **When** quality is read, **Then** it names which submetrics contributed and which were unavailable.
4. **Given** a submetric that cannot be computed, **When** the score is formed, **Then** it is omitted rather than defaulted to a neutral value.

---

### Edge Cases

- What happens when every close in the window is identical? The slope is zero and the residuals vanish, so the bands collapse onto the centre. The snapshot must report this rather than divide by zero.
- What happens when the lookback exceeds the available history? The fit refuses. Fitting on fewer points than asked for silently changes the model.
- What happens when a bar carries a non-positive close? Log price is undefined; the fit refuses and names the bar.
- What happens when two fits run at the same `as_of` over the same data? Identical snapshots, byte for byte — otherwise "the channel changed" and "we recomputed" are indistinguishable.
- What happens when bars arrive out of order in the input? They are ordered by event time before fitting; input order is not market information.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The model MUST fit an ordinary least squares line to log close price over a configurable lookback of finalized bars.
- **FR-002**: The centre MUST be the exponential of the fitted log-price line.
- **FR-003**: Upper and lower bands MUST come from empirical quantiles of the fit residuals, at configurable levels defaulting to 0.90 and 0.10.
- **FR-004**: The snapshot MUST report `slope_normalized` as the fitted slope divided by the residual standard deviation, per ADR-007.
- **FR-005**: The snapshot MUST report the channel width as a percentage of the centre.
- **FR-006**: The snapshot MUST carry `as_of`, model name, model version, lookback, and `source_max_event_time`.
- **FR-007**: `source_max_event_time` MUST be at or before `as_of`, and the model MUST refuse to produce a snapshot that violates this.
- **FR-008**: Bars whose event time exceeds `as_of` MUST be excluded from the fit.
- **FR-009**: Only finalized bars MUST be used.
- **FR-010**: The fit MUST refuse when fewer bars than the lookback are available, and MUST say so.
- **FR-011**: The fit MUST refuse when any close in the window is not positive, and MUST name the offending bar.
- **FR-012**: The snapshot MUST carry a quality score in `[0,1]` composed of the submetrics ADR-007 lists, with configurable weights.
- **FR-013**: The snapshot MUST record which submetrics contributed and which were unavailable.
- **FR-014**: An unavailable submetric MUST be omitted from the average rather than given a neutral default.
- **FR-015**: Snapshots MUST be immutable once produced.
- **FR-016**: Two fits over the same data at the same `as_of` MUST produce identical snapshots.

### Key Entities

- **Channel snapshot**: the channel as it stood at one moment, with enough provenance to prove it could not have seen later data.
- **Channel quality**: a score and an honest account of what went into it.
- **Channel model**: the fitting procedure, named and versioned so snapshots from different definitions stay distinguishable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Refitting at an unchanged `as_of` after appending later bars produces an identical snapshot.
- **SC-002**: A snapshot's `source_max_event_time` never exceeds its `as_of`, across every test series.
- **SC-003**: Fitting a series constructed with a known log-linear slope recovers that slope within the constructed noise.
- **SC-004**: Two series identical in shape but scaled to different price levels yield equal normalized slopes.
- **SC-005**: Coverage on a series that respects its bands is close to the configured band width.
- **SC-006**: A clean trend scores materially higher than pure noise.
- **SC-007**: A quality score names its contributing submetrics, and omits rather than defaults the unavailable ones.
- **SC-008**: Fitting with insufficient history, or with a non-positive close, refuses with a message identifying the cause.

## Assumptions

- The model consumes finalized `Bar` values from REQ-WP-005. Unfinalized bars are excluded by FR-009 rather than filtered by the caller, so the rule cannot be forgotten.
- Storage is append-only in the sense that a snapshot is immutable and a new fit produces a new snapshot; no persistence layer is built here. PRD §29.6's `channel_snapshots` table is a later concern, and §0.5's prohibition on rewriting them is honoured by the values being frozen.
- Forecast horizons are out of scope. PRD §13.1's snapshot carries them and §13.7 defines them; this is Baseline A only, and an empty forecast list is honest where a fabricated one would not be.
- The quality weights are a starting point, not a finding. PRD §48 lists the research questions that must be answered before any of this drives a decision.
- Only Baseline A is built. Baselines B through E of §13.3-13.6 are separate models behind the same interface.
