---
traces: [REQ-WP-057]
status: draft
---

# Feature Specification: The performance targets are measured, and the thing that would break them is what is asserted

**Feature Branch**: `wp-057-load-tests`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-057 — Phase 8's load tests.

## Context

PRD §45's Phase 8 lists "load tests" and never defines them; §36 states the
targets. Measured against the real code first, because the numbers change what
is worth asserting:

    chart historical load, 2,000 bars    p95   26ms   against 2,000ms
    the slowest of four channel models   p95  1.3ms   against 2,000ms
    a feature update                     p95  4.7µs   against 1,000ms

Between seventy and two hundred thousand times of headroom. Two consequences
pointing in opposite directions: a test asserting §36's targets keeps passing
through a fortyfold regression, and a test asserting a tight threshold measures
the runner — the spread between fastest and slowest read within a single run on
one machine was already 2.32×.

**So the assertion that earns its place is about scaling.** The read costs about
9µs a row and a doubling takes 1.8–1.9 times as long. A change making it
quadratic passes a two-second threshold at two thousand bars and falls over at
twenty thousand, and a ratio between two measurements from the same run divides
the machine out.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The promises are measured (Priority: P1)

**Acceptance Scenarios**:

1. **Given** 2,000 bars, **When** loaded through the real read path, **Then** the p95 is inside §36's budget.
2. **Given** each channel model, **When** fitted, **Then** it is inside the signal budget.
3. **Given** a feature update, **When** timed, **Then** it is inside its budget.
4. **Given** any of these, **When** reported, **Then** the headroom is stated alongside.

---

### User Story 2 - The regression that matters is caught (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a doubling series, **When** the read is measured, **Then** each doubling costs less than three times the last.
2. **Given** a deliberately quadratic operation, **When** measured the same way, **Then** the guard refuses it.
3. **Given** a deliberately linear one, **When** measured, **Then** the guard passes it.

---

### User Story 3 - The instrument is right (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a run with one slow outlier, **When** a p95 is taken, **Then** it is a sample that happened and not a mean.
2. **Given** a growing measurement, **When** headroom is computed, **Then** it shrinks.
3. **Given** one measurement, **When** a scaling ratio is asked for, **Then** it is refused.

### Edge Cases

- **A measurement with no samples.** Measured nothing; refused.
- **A run of zero repeats.** Refused where it is asked for, not three layers down.
- **A machine ten times slower.** The same ratios.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: §36's targets MUST be measured against the real code paths.
- **FR-002**: Each target MUST be asserted.
- **FR-003**: The headroom MUST be reported alongside each measurement.
- **FR-004**: Scaling MUST be asserted as a ratio between measurements from one run.
- **FR-005**: The scaling guard MUST be shown to refuse a quadratic operation and to pass a linear one.
- **FR-006**: A percentile MUST be a sample that occurred, never an interpolation or a mean.
- **FR-007**: Headroom MUST shrink as a measurement grows.
- **FR-008**: An empty measurement, a fraction outside a run, a single-point scaling series and a zero-repeat run MUST each be refused.
- **FR-009**: The measurements MUST need no service beyond a temporary warehouse.

### Key Entities

- **Target**: one of §36's promises and its budget.
- **Measurement**: what a run cost, in order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Three targets measured and asserted, each reporting headroom.
- **SC-002**: The read's doubling ratios are below three; a quadratic operation's are not.
- **SC-003**: A linear operation passes the same guard.
- **SC-004**: The measurement arithmetic is tested independently of what it measures.

## Assumptions

- **This is not a load test in the usual sense.** Nothing generates concurrent
  traffic against a deployed system, because nothing is deployed.
- **§36's other targets are out of scope**, each for a reason: the Telegram
  target times a call [[ADR-018]] made the caller's, and the symbol and level
  counts are capacities rather than latencies.

## Open Questions

- **Whether the measurements should be recorded over time.** Headroom is
  reported per run and nothing keeps it, so a slow drift is visible only to
  somebody comparing two runs by eye.
