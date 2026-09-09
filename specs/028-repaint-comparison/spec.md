---
traces: [REQ-US-003]
status: draft
---

# Feature Specification: Comparing the channel that existed against the model's later state

**Feature Branch**: `us-003-repaint-comparison`

**Created**: 2026-09-09

**Input**: REQ-US-003 — "the historical channel snapshot as it existed at the
time is available for comparison against the model's current/later state." PRD
§27.5, §35.3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Put the two channels side by side (Priority: P1)

One answer holding the stored snapshot for an instant and a refit over history
up to a later instant, with the difference between them measured.

**Why this priority**: PRD §27.5 calls the distinction critical because it
"directly exposes repaint-like differences". Exposing it through a toggle asks
the reader to hold six numbers in their head and subtract; the difference is the
measurement, so the answer should contain it.

**Acceptance Scenarios**:

1. **Given** a stored snapshot and later history, **When** a comparison is requested, **Then** it carries both channels and the difference between them.
2. **Given** the two channels, **When** the difference is read, **Then** it gives the centre, boundary, slope, width and quality deltas.
3. **Given** a centre that moved, **When** the difference is read, **Then** the movement is also expressed as a share of the channel's own width, so it can be compared across instruments.
4. **Given** no stored snapshot at the instant, **When** a comparison is requested, **Then** it is refused — `AS-SEEN-THEN` cannot be reconstructed after the fact.
5. **Given** too little history to refit, **When** a comparison is requested, **Then** it is refused rather than approximated over fewer bars.

---

### User Story 2 - Know exactly how much hindsight is in the refit (Priority: P1)

The comparison states how far past the instant its refit was allowed to see.

**Why this priority**: a refit over later bars is a channel that has seen what
followed. That is the whole point of the comparison and the one thing that must
never be mistaken for a point-in-time value.

**Acceptance Scenarios**:

1. **Given** a comparison, **When** it is read, **Then** it states the span of hindsight the refit had, in nanoseconds.
2. **Given** a later instant equal to the signal's, **When** the comparison is made, **Then** the hindsight is zero and the comparison measures model drift alone.
3. **Given** a later instant before the signal's, **When** a comparison is requested, **Then** it is refused — a later state that is earlier is not one.
4. **Given** a comparison, **When** it is read, **Then** it declares itself research-only.
5. **Given** the signal, alerting and stop packages, **When** their sources are inspected, **Then** none imports the comparison module.

---

### Edge Cases

- What happens when the two channels are identical? Every delta is zero, and that is a result: the model has not drifted and nothing repainted over the span asked about.
- What happens when the stored snapshot came from a different model version? The comparison still runs and both versions are reported. Comparing across versions is a legitimate question, and refusing it would hide a drift that only shows up that way.
- What happens when the channel width is zero in the stored snapshot? The width-relative figure is refused for that comparison while the absolute deltas stand — dividing by a zero width would report an infinite repaint.
- What happens when the later instant is far past the data? The refit uses what exists; the hindsight span still says how far the question reached.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A comparison MUST carry the stored snapshot at the instant and a refit over history up to a caller-supplied later instant.
- **FR-002**: A comparison MUST report the centre, upper, lower, slope, width and quality deltas between them.
- **FR-003**: The centre movement MUST also be reported as a share of the stored channel's width.
- **FR-004**: A width-relative figure MUST be refused, not infinite, when the stored width is zero.
- **FR-005**: A comparison MUST be refused when no snapshot was stored at or before the instant.
- **FR-006**: A comparison MUST be refused when the history cannot support a refit.
- **FR-007**: A comparison MUST state its hindsight span, the distance from the instant to the later instant.
- **FR-008**: A later instant before the instant MUST be refused.
- **FR-009**: Every comparison MUST declare itself research-only.
- **FR-010**: No module on the signal, alerting or stop path may import the comparison.
- **FR-011**: Both channels' model names and versions MUST be reported, and a version difference MUST NOT refuse the comparison.

### Key Entities

- **Comparison**: the two channels, their differences, the hindsight span, and the research-only marking.
- **Difference**: one delta per channel property, plus the width-relative centre movement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A comparison contains both channels and every delta, checked against hand arithmetic.
- **SC-002**: The width-relative centre movement matches a hand-computed ratio, and refuses on a zero width.
- **SC-003**: A missing snapshot refuses; a refit that cannot be made refuses.
- **SC-004**: The hindsight span equals the distance between the two instants, and is zero when they are equal.
- **SC-005**: An inverted pair of instants refuses.
- **SC-006**: Every comparison declares itself research-only.
- **SC-007**: No signal-path module imports the comparison, verified over the source.

## Assumptions

- **The later instant is the caller's.** PRD §27.5 says the refit is "calculated now over visible/current history", and what is visible is the reader's window — so the span is an argument rather than a clock reading.
- **The comparison is an API answer, not a chart.** REQ-US-003's acceptance asks that the snapshot be "available for comparison"; the chart's two modes already exist for looking at one at a time.
- **The refit uses the same fitter as production**, not a copy, so a difference is the data's and not the arithmetic's.
