---
traces: [REQ-WP-019, REQ-NRT-A, REQ-NRT-B, REQ-NRT-C, REQ-NRT-D, REQ-NRT-E]
status: draft
---

# Feature Specification: Causal turning points

**Feature Branch**: `wp-019-turning-points`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-019 — PRD §13A's turning point engine. REQ-NRT-A through
REQ-NRT-E — §13A.28's mandatory non-repainting tests, all `hard_gated`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Know when a high was, and when we could know it (Priority: P1)

A confirmed extremum records two different times: when the price made the high,
and when the system was first legally able to say so.

**Why this priority**: PRD §13A.1 is the section the whole engine rests on.
`extremum_time != known_at` is expected, and "any backtest that acts on the
10:00 label before 10:30 is invalid". Every other story here is a way of
producing those two timestamps correctly.

**Independent Test**: Feed a price series with a known high, and assert the
confirmed extremum's `extremum_time` is the high's bar and `known_at` is the
bar the reversal threshold was crossed on.

**Acceptance Scenarios**:

1. **Given** a price series that peaks and then reverses past the threshold, **When** the extremum is confirmed, **Then** `extremum_time` is the peak's bar and `known_at` is the crossing bar.
2. **Given** the same series, **When** the confirmation lag is read, **Then** it is the number of bars between them.
3. **Given** a peak that never reverses far enough, **When** the series ends, **Then** no extremum is confirmed — a running high is not a high.
4. **Given** a confirmed extremum, **When** it is compared with the price series, **Then** `known_at >= extremum_time` always.

---

### User Story 2 - A reversal threshold that adapts (Priority: P1)

The threshold that confirms a reversal is computed from the market's own
volatility at that moment, not fixed once.

**Why this priority**: PRD §13A.5 requires the adaptive threshold and §13A.29's
second named failure mode is "fixed threshold failing across volatility
regimes". P1 with US1 because a detector with the wrong threshold produces
correct timestamps for the wrong events.

**Independent Test**: Run the same series under each threshold mode and assert
the confirmations differ where the modes differ.

**Acceptance Scenarios**:

1. **Given** a fixed basis-point mode, **When** a reversal exceeds it, **Then** the extremum confirms.
2. **Given** an ATR-multiple mode, **When** volatility rises, **Then** the threshold rises with it.
3. **Given** a hybrid mode, **When** it is evaluated, **Then** it is the maximum of its components, never less than the floor.
4. **Given** any mode, **When** a threshold is computed at time `t`, **Then** it uses only data with `event_time <= t`.

---

### User Story 3 - Not be told about every wiggle (Priority: P2)

A pivot too small to matter is not reported.

**Why this priority**: PRD §13A.6, and §13A.29's first named failure mode is
"tiny noisy pivots generating alert spam". P2 because it filters output the
detector already produces correctly.

**Independent Test**: A series of small oscillations around a trend, and one
large swing; assert only the large one is reported.

**Acceptance Scenarios**:

1. **Given** a swing whose prominence is below the minimum, **When** it would confirm, **Then** it is not reported as a confirmed extremum.
2. **Given** two extrema closer together than the minimum bar separation, **When** the second would confirm, **Then** it is rejected.
3. **Given** a prominent swing, **When** it confirms, **Then** its prominence is reported in both basis points and ATR multiples.

---

### User Story 4 - Prove the outputs do not repaint (Priority: P1)

The engine's outputs, once known, never change — and the tests that prove it
are part of the product.

**Why this priority**: PRD §13A.28 calls these tests mandatory. Five of them are
`hard_gated` requirements in this repository, which validator rule R5 never
waives. PRD §2.1 names repainting as the risk the product exists to avoid.

**Independent Test**: Each of the five tests, run against the engine.

**Acceptance Scenarios**:

1. **Test A, future-bar invariance**: **Given** outputs computed up to `t`, **When** arbitrary bars are appended after `t`, **Then** every finalized output with `available_at <= t` is unchanged, field for field.
2. **Test B, candidate chronology**: **Given** a candidate that is later invalidated, **When** its original record is read, **Then** it is unchanged — invalidation is a new record, not an edit.
3. **Test C, confirmation legality**: **Given** a confirmation, **When** its inputs are examined, **Then** `known_at >= extremum_time` and no input carries `available_at > known_at`.
4. **Test D, centered filter prohibition**: **Given** a transform declaring symmetric or centered future dependence, **When** the production path is asked to use it, **Then** it is refused.
5. **Test E, replay parity**: **Given** one event stream and one configuration, **When** it is replayed, **Then** the outputs match the live run exactly.

---

### Edge Cases

- What happens when the series starts mid-swing? The first running extreme establishes the state; no extremum is confirmed until a reversal crosses the threshold, because the direction before the data began is unknown.
- What happens when price gaps past the threshold in one bar? The extremum confirms on that bar, and `known_at` is that bar. A gap does not let confirmation be backdated.
- What happens when the threshold cannot be computed for want of history? No confirmation is attempted, and the reason is recorded — approximating a threshold over insufficient history would produce a confirmation nobody could reproduce.
- What happens when two candidate extrema occur at the same bar? Impossible for one instrument and timeframe: the detector is in exactly one direction at a time.
- What happens when a confirmed extremum is followed by an even higher high before the next confirmation? The confirmation stands. PRD §13A.2's lifecycle is append-only, and a later high is a new candidate, not a correction of the old one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every extremum-related output MUST carry `extremum_time` and `known_at`.
- **FR-002**: `known_at` MUST be at or after `extremum_time` for every confirmed extremum.
- **FR-003**: A high MUST confirm only after price reverses from the running high by at least the threshold; a low, symmetrically.
- **FR-004**: Confirmation lag MUST be reported in bars.
- **FR-005**: The threshold MUST support fixed basis points, ATR multiple, realized-volatility multiple, channel-width fraction, and a hybrid taking the maximum.
- **FR-006**: A threshold at time `t` MUST use only data with `event_time <= t`, and MUST NOT be recomputed for a past swing.
- **FR-007**: A confirmed extremum MUST report reversal distance and prominence in basis points, and prominence in ATR multiples when ATR is available.
- **FR-008**: An extremum below the configured minimum prominence, or too close to the previous one, MUST NOT be reported as confirmed.
- **FR-009**: Every emitted record MUST be immutable once produced.
- **FR-010**: An invalidation MUST be a new record; no existing record may be edited.
- **FR-011**: The production path MUST refuse any transform that declares symmetric or centered future dependence.
- **FR-012**: No module in the engine may consult a system clock.
- **FR-013**: Replaying one event stream under one configuration MUST produce outputs identical to the live run.
- **FR-014**: Appending bars after `t` MUST NOT change any output whose `available_at` is at or before `t`.

### Key Entities

- **Extremum candidate**: a running high or low, when it occurred, and what was known when it was observed.
- **Confirmed extremum**: a candidate whose reversal crossed the threshold, with both timestamps and the lag between them.
- **Threshold policy**: how far price must reverse, computed point-in-time.
- **Transform declaration**: whether a transform looks forward, stated by the transform itself.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a constructed series, the confirmed extremum's two timestamps match hand-identified bars.
- **SC-002**: `known_at >= extremum_time` holds for every confirmation over a long generated series.
- **SC-003**: Each threshold mode produces the confirmations hand-computed for it, and they differ between modes.
- **SC-004**: A sub-threshold swing produces no confirmation; a prominent one does.
- **SC-005**: Appending arbitrary bars after `t` leaves every output with `available_at <= t` byte-identical (Test A).
- **SC-006**: An invalidated candidate's original record is unchanged (Test B).
- **SC-007**: No confirmation reads an input with `available_at > known_at` (Test C).
- **SC-008**: A centered transform is refused by the production path (Test D).
- **SC-009**: A replayed stream produces outputs identical to the live run (Test E).
- **SC-010**: No module in the package references a system clock, verified over the source.

## Assumptions

- **Two of REQ-WP-019's five acceptance criteria are not met by this feature, and cannot be.** "Direct baseline metrics exist" needs PRD §13A.13's supervised targets, which need REQ-WP-017's point-in-time dataset; "derivative experiment can return `NO_EDGE`" needs REQ-WP-018's GMDH. Principle IV forbids the ML layer until deterministic baselines pass leakage tests, which is what this feature produces. REQ-WP-019 therefore does not reach `implemented` here.
- **REQ-NRT-F is not in scope** for the same reason: it tests GMDH derivative root stability, and there is no GMDH.
- **This is PRD §13A.30's step 2.** Steps 3 to 5 — causal local-polynomial slope, Kalman, channel-conditioned classes — are named in REQ-WP-019's ordering and are not built here; step 2 is what the non-repainting tests can be written against.
- **`TurningPointForecast` (§13A.19) is not implemented.** It is a model output, and there is no model.
- Kafka topics (§13A.20) and storage (§13A.21) are unbuilt, as is everything else that needs PRD §29.
- Chart overlays (§13A.25) and alert integration (§13A.24) are named in REQ-WP-019's ordering and left for when the structural baseline has proven itself.
