---
traces: [REQ-WP-028]
status: draft
---

# Feature Specification: Extrema on the chart, never before they were known

**Feature Branch**: `wp-028-extremum-markers`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-028 — Phase 1A's last deliverable and the acceptance criterion that governs it.

## Context

The detector produces an `ExtremumCandidate` while a swing is forming and a
`ConfirmedExtremum` when the reversal crosses its threshold. The confirmed one
carries three things that matter here: when the turn happened
(`extremum_time_ns`), when it became knowable (`known_at_ns`), and the lag
between them.

Neither reaches a table, a repository, an endpoint or the chart.

PRD §45's Phase 1A states what must be true once they do:

    - no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;

That is the whole feature. A marker at `extremum_time_ns` on a chart showing the
past as it was seen then claims the system knew about a turn before it did — the
repaint §13A.1 forbids, drawn on a screen where it will be believed. A candidate
drawn like a confirmation makes the same claim more quietly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extrema survive and are served (Priority: P1)

**Acceptance Scenarios**:

1. **Given** confirmed extrema and candidates written to the plane, **When** they are read back, **Then** every field matches, timestamps and prices included.
2. **Given** either repository implementation, **When** the same window is asked for, **Then** the answers match.
3. **Given** two instruments, **When** one is asked for, **Then** the other's are not returned.

---

### User Story 2 - A confirmation never appears before it was known (Priority: P1)

**Why this priority**: The phase's own acceptance criterion, and the only part of
this feature that can be wrong in a way that misleads rather than annoys.

**Acceptance Scenarios**:

1. **Given** a confirmed extremum whose turn was at `t0` and which became knowable at `t1`, **When** the chart is read as seen at any instant before `t1`, **Then** it does not appear.
2. **Given** the same extremum, **When** the chart is read at `t1` or later, **Then** it appears at `t0` — the turn is drawn where it happened, once it is allowed to be drawn at all.
3. **Given** later bars appended, **When** an earlier instant is read again, **Then** what it shows is unchanged.

---

### User Story 3 - A candidate is not a confirmation (Priority: P1)

**Acceptance Scenarios**:

1. **Given** both on one chart, **When** they are drawn, **Then** they are distinguishable.
2. **Given** a candidate that was later confirmed, **When** the chart is read after confirmation, **Then** one turn is shown rather than two.
3. **Given** a candidate that was never confirmed, **When** the chart is read, **Then** it is still shown as a candidate — a swing that did not confirm is a fact, not an error.

### Edge Cases

- **`known_at_ns` equal to the instant asked about.** Shown: the boundary is inclusive, and stating it is the point of saying so.
- **A candidate observed after the instant asked about.** Not shown, by the same rule its confirmation obeys.
- **Two extrema at one instant.** Both shown; the chart is not the place to break a tie the data does not.
- **An extremum outside the window.** Not shown, and that is a window question rather than a knowledge one — the two filters are separate and both apply.
- **`CURRENT REFIT` mode.** Out of scope for the filter: PRD §27.5 makes that mode the place where repaint-like differences are meant to be visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Confirmed extrema and candidates MUST be stored on the canonical plane and read back field for field.
- **FR-002**: Both repository implementations MUST answer alike.
- **FR-003**: An endpoint MUST serve them for a window of an instrument and timeframe.
- **FR-004**: A caller MUST be able to ask as of an instant.
- **FR-005**: As of instant `t`, a confirmed extremum MUST be returned only when `known_at_ns <= t`.
- **FR-006**: As of instant `t`, a candidate MUST be returned only when `observed_at_ns <= t`.
- **FR-007**: A confirmed extremum MUST be drawn at its `extremum_time_ns` once it is returned at all.
- **FR-008**: Candidates and confirmations MUST be distinguishable on the chart.
- **FR-009**: A candidate that was confirmed MUST NOT be drawn twice.
- **FR-010**: A candidate that was never confirmed MUST still be drawn.
- **FR-011**: Appending later data MUST NOT change what an earlier instant shows.
- **FR-012**: What the chart already draws MUST be unchanged.

### Key Entities

- **Confirmed extremum**: a turn, when it happened, and when it became knowable.
- **Candidate**: a swing that has not confirmed, and when it was observed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every stored field reads back equal, prices as decimals.
- **SC-002**: The behavioural suite passes against both repositories.
- **SC-003**: Asking as of one nanosecond before `known_at_ns` returns nothing; asking at it returns the extremum.
- **SC-004**: A returned confirmation's drawn position equals its `extremum_time_ns`.
- **SC-005**: Candidates and confirmations produce different markers.
- **SC-006**: A confirmed turn yields one marker, not two.
- **SC-007**: Two reads of one instant, before and after later data arrives, are equal.
- **SC-008**: Every existing chart and endpoint test passes unchanged.

## Assumptions

- **Nothing here re-derives an extremum.** The detector's output is stored, served and drawn; where a value is computed stays with [[REQ-WP-019]].
- **The decision about what to draw is testable without rendering**, as this application already requires of its chart.
- **How the two markers differ is the plan's.** Shape, colour or fill are all honest; being told apart is the requirement.
- **`CURRENT REFIT` keeps its meaning.** The knowledge filter is `AS-SEEN-THEN`'s, and the other mode is where differences are meant to show.
