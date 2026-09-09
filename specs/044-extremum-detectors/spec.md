---
traces: [REQ-EXP-011]
status: draft
---

# Feature Specification: Structural extremum detector comparison

**Feature Branch**: `exp-011-extremum-detector`

**Created**: 2026-09-09

**Input**: REQ-EXP-011 — five non-repainting swing methods, five metrics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run all five threshold methods through one detector (Priority: P1)

Fixed bps, ATR, realized vol, channel width, hybrid — the production detector's
own five modes.

**Why this priority**: the non-repainting guarantee lives in the lifecycle, so a
comparison that reimplemented it would be comparing its own copy.

**Acceptance Scenarios**:

1. **Given** the five methods, **When** the comparison runs, **Then** each has an entry.
2. **Given** a method that confirms nothing, **When** its entry is read, **Then** it says so rather than reporting a zero rate.
3. **Given** the channel-width method and no channel model, **When** the comparison runs, **Then** it is reported as unavailable, not as a method that found nothing.
4. **Given** a channel model, **When** that method runs, **Then** it confirms at a rate in line with the others.

---

### User Story 2 - Report the five metrics that pull against each other (Priority: P1)

Confirmation lag, extrema per thousand bars, prominence, regime stability,
downstream expectancy.

**Why this priority**: a detector that confirms sooner confirms more and
confirms noise. Collapsing five metrics into a ranking would hide the trade-off
the experiment exists to show.

**Acceptance Scenarios**:

1. **Given** a method that fired, **When** its entry is read, **Then** all five metrics are present.
2. **Given** any confirmation, **When** its lag is read, **Then** it is at least one bar.
3. **Given** higher costs, **When** expectancy is recomputed, **Then** it falls.
4. **Given** the report, **When** it is read, **Then** nothing is ranked and the trade-off is stated.

---

### User Story 3 - Measure stability across volatility regimes (Priority: P1)

Each series is split at its own median volatility, and each method's rate is
reported per regime.

**Why this priority**: a fixed threshold finds a swing every other bar in a
storm and nothing in a drift. "Adaptive" is a claim, and this is where it is
checked.

**Acceptance Scenarios**:

1. **Given** a series that changes regime, **When** it is split, **Then** roughly half the bars fall in each.
2. **Given** a series quiet for four fifths, **When** it is split, **Then** the split is still even — the cut is the median, not one bar's reading.
3. **Given** confirmations in both regimes, **When** they are attributed, **Then** each belongs to the regime of the bar it was confirmed on.
4. **Given** two methods, **When** their ratios are compared, **Then** the fixed threshold is no more stable than the adaptive one.
5. **Given** any ratio, **When** it is read, **Then** it is at least one — busier over quieter.

---

### Edge Cases

- What happens when a method fires in only one regime? Its ratio is absent rather than infinite, and both regime rates are still reported.
- What happens during the warm-up, before a threshold can be computed? Those bars are skipped, which is a fact about the warm-up rather than about the method.
- What happens when a confirmation lands after the last bar the horizon needs? It is dropped from the expectancy and still counted as an extremum — it happened, it just cannot be traded in this window.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All five methods MUST run through the production detector.
- **FR-002**: A method that confirms nothing MUST report the reason.
- **FR-003**: The channel-width method MUST be reported unavailable without a channel model, and MUST use the model's own width when given one.
- **FR-004**: The channel width MUST be interpreted in `ChannelSnapshot.width_pct`'s units.
- **FR-005**: The five metrics MUST be reported for every method that fired.
- **FR-006**: A confirmation lag MUST be at least one bar.
- **FR-007**: Volatility regimes MUST be split at the series' own median.
- **FR-008**: An extremum MUST be attributed to the regime of its confirmation bar.
- **FR-009**: The regime ratio MUST be the busier rate over the quieter.
- **FR-010**: Expectancy MUST be computed after costs, and a missing cost model MUST be refused.
- **FR-011**: Nothing MUST be ranked, and the trade-off MUST be stated in the report.
- **FR-012**: The report MUST be deterministic.

### Key Entities

- **Detector entry**: one method's five metrics, or why it has none.
- **Regime rate**: one volatility regime's bars and extrema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Five entries, one per method.
- **SC-002**: A silent method reports its reason.
- **SC-003**: The channel method is unavailable without a model and fires with one.
- **SC-004**: Its rate stays in line with the others on a choppy series.
- **SC-005**: All five metrics present for a method that fired.
- **SC-006**: Every median lag is at least one bar.
- **SC-007**: A median split divides any series roughly in half.
- **SC-008**: Extrema appear in both regimes and sum to the total.
- **SC-009**: Every ratio is at least one; the fixed method is no more stable than the adaptive one.
- **SC-010**: Higher costs lower expectancy; no cost model refuses.
- **SC-011**: Nothing is ranked.
- **SC-012**: Two runs produce equal reports.

## Assumptions

- **The detector is [[REQ-WP-019]]'s**, unchanged except for accepting the channel width its own threshold mode always needed.
- **The exit rule for expectancy is fixed and symmetric**, as in every other experiment here.
