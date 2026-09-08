---
traces: [REQ-WP-013, REQ-BIAS-005]
status: draft
---

# Feature Specification: Derivatives feature engine

**Feature Branch**: `wp-013-derivatives`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-013 — funding/OI/basis/liquidations; z-scores; state joins.
REQ-BIAS-005 — no using current funding settlement before it becomes known.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read funding without reading the future (Priority: P1)

Funding features describe the rate that was in force and known at `t`, never
the settlement that had not happened yet.

**Why this priority**: PRD §41 rule 5 names it, and it is the derivatives
family's characteristic leak. A funding rate settles at fixed intervals; the
rate for the interval containing `t` is not final at `t`, and using it is
using a number the market did not have.

**Independent Test**: A state whose `next_funding_time` is after `t`, and one
whose settlement has passed; assert only the settled one is used.

**Acceptance Scenarios**:

1. **Given** a state whose next funding time is after `t`, **When** funding features are computed at `t`, **Then** the unsettled rate is not treated as settled.
2. **Given** a series of settled rates, **When** the z-score is computed, **Then** it uses only rates settled at or before `t`.
3. **Given** fewer observations than the window needs, **When** a z-score is requested, **Then** it refuses rather than computing over what exists.
4. **Given** a constant funding history, **When** the z-score is computed, **Then** it refuses — a zero standard deviation has no z-score, and reporting zero would read as "perfectly average".

---

### User Story 2 - See what open interest is doing (Priority: P1)

Open interest, its change over several windows, its z-score, its ratio to
volume, and which of PRD §16.2's four regimes price and OI are jointly in.

**Why this priority**: PRD §16.2. The regime matrix is the piece most likely to
be misused, and the PRD is explicit about how: it is "stored as feature, not
hard-coded trading truth".

**Independent Test**: Constructed OI and price series for each of the four
quadrants.

**Acceptance Scenarios**:

1. **Given** OI observations, **When** the change over a window is read, **Then** it is the difference from the observation at or before the window's start.
2. **Given** price rising and OI rising, **When** the regime is read, **Then** it is the one PRD §16.2 names for that quadrant.
3. **Given** any regime, **When** it is read, **Then** it is a label, and nothing in this package acts on it.
4. **Given** volume of zero, **When** the OI-to-volume ratio is read, **Then** it is absent rather than infinite.

---

### User Story 3 - Measure the gap between perp and spot (Priority: P2)

Basis in basis points, and the mark-to-index premium.

**Why this priority**: PRD §16.3. P2 because both are arithmetic over values
the connector already normalizes.

**Acceptance Scenarios**:

1. **Given** a perp price and a spot price, **When** basis is read, **Then** it is their difference relative to spot, in basis points.
2. **Given** a mark and an index price, **When** the premium is read, **Then** it is their difference relative to the index, in basis points.
3. **Given** a missing spot or index price, **When** either is read, **Then** it is absent rather than zero.

---

### User Story 4 - Aggregate forced selling (Priority: P2)

Liquidation notional by side over windows, the net imbalance, intensity against
traded volume, clusters by price, and time since the last spike.

**Why this priority**: PRD §16.4.

**Acceptance Scenarios**:

1. **Given** liquidations in a window, **When** totals are read, **Then** long and short notional are separate.
2. **Given** both sides, **When** the imbalance is read, **Then** it is their difference over their sum, and absent when both are zero.
3. **Given** liquidations at nearby prices, **When** clusters are read, **Then** they are grouped by price bucket with their total notional.
4. **Given** a spike, **When** time since it is read, **Then** it is measured in event time from the spike's own event.

---

### User Story 5 - Know what every number means (Priority: P1)

Every feature this package exposes is in the registry PRD §19 requires.

**Why this priority**: REQ-PRIN-008 and ADR-015. The registry was built with
REQ-WP-011's features and is enforced by a test; a second package producing
features must extend it or the gate stops meaning anything.

**Acceptance Scenarios**:

1. **Given** the package's features, **When** the registry is checked, **Then** every one has a complete entry.
2. **Given** a new derivatives feature without a registration, **When** the suite runs, **Then** it fails by name.

---

### Edge Cases

- What happens when funding has never settled in the available history? Funding features are absent, not zero — no settlement is not a settlement of zero.
- What happens when two derivatives states share an event time? The one with the later ingest time is later information about the same instant; if those match too, the state join refuses, because nothing in the data breaks the tie.
- What happens when open interest is reported in base units only? The USD figures are absent; multiplying by a price we chose would invent a number the venue did not report.
- What happens when a liquidation's notional is zero? It counts toward the event count and contributes nothing to notional totals — a zero-notional print is a data quality signal, not an absence.
- What happens when the window for a z-score contains a gap? The observations that exist are used and their count is reported, so a z-score over four points is distinguishable from one over forty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A funding feature at `t` MUST use only rates whose settlement time is at or before `t`.
- **FR-002**: A z-score MUST refuse when fewer observations exist than its window requires.
- **FR-003**: A z-score MUST refuse when the standard deviation is zero.
- **FR-004**: Funding features MUST include the current settled rate, trailing mean and standard deviation, the z-score, and acceleration.
- **FR-005**: Open interest features MUST include the USD level, changes over configurable windows, a z-score, and the ratio to traded volume.
- **FR-006**: The price/OI regime MUST be one of PRD §16.2's four labels, and MUST be reported as a value with no action attached.
- **FR-007**: A ratio with a zero denominator MUST be absent, never infinite or zero.
- **FR-008**: Basis MUST be reported in basis points relative to spot, and the mark premium relative to the index.
- **FR-009**: Liquidation aggregates MUST separate long and short notional, and report their imbalance, intensity, clusters and time since the last spike.
- **FR-010**: A state join MUST take the latest state at or before the instant asked about, and MUST refuse an unbreakable tie.
- **FR-011**: Every feature exposed MUST carry a registry entry with all of PRD §19's fields.
- **FR-012**: No module in this package may consult a system clock.
- **FR-013**: Every window MUST be event-time.

### Key Entities

- **Funding observation**: a rate, when it settled, and when it became knowable.
- **Open interest observation**: a level and the instant it describes.
- **Liquidation aggregate**: what was forced out, on which side, over a window.
- **Regime**: a label for the joint direction of price and open interest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A funding rate whose settlement is after `t` does not appear in any feature at `t`.
- **SC-002**: A z-score over too few observations, or over a constant series, refuses.
- **SC-003**: Each of PRD §16.2's four regimes is produced for a series constructed to be in it.
- **SC-004**: Basis and premium match hand-computed values.
- **SC-005**: Liquidation aggregates match hand-computed totals, and the imbalance is absent when nothing was liquidated.
- **SC-006**: A state join never returns a state later than the instant asked about.
- **SC-007**: The exposed and registered feature sets are equal.
- **SC-008**: No module references a system clock.

## Assumptions

- **Cross-venue features are out of scope.** PRD §16.1's funding dispersion and §16.3's CEX-to-CEX basis dispersion are REQ-WP-016; §16.3's DEX comparison is REQ-WP-014 and REQ-WP-015.
- **PRD §16.5's long/short ratios are not built.** The PRD calls them optional and requires them to be "labeled provider-specific and not assumed to represent the whole market"; without a second provider to compare against, the label would be the only content.
- **No storage.** As everywhere else, the observations are in memory.
- **Predicted funding is passed through, not modelled.** §16.1 says "when source provides it"; nothing here forecasts a rate.
