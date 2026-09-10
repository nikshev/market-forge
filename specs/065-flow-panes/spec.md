---
traces: [REQ-WP-027]
status: draft
---

# Feature Specification: Selectable lower panes for order flow

**Feature Branch**: `wp-027-flow-panes`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-027 — PRD §27.3's selectable panes, and Phase 2's last deliverable.

## Context

The chart draws candles, a channel, zones, a signal marker and a volume profile.
PRD §27.3 asks for selectable lower panes and the app has none.

Phase 2's subject is the order book and order flow, and its features are already
registered and already served: `cvd`, `cvd_slope`, `ofi_1s` … `ofi_1m`,
`ofi_bar`, `depth_imbalance_*`. `GET /api/v1/features/timeseries` returns a point
per instant carrying a mapping of feature name to value.

**That mapping is where this feature can go wrong.** A point that carries no
value for the selected feature is silent, not zero. Drawn as zero it becomes a
reading — a flat line through the middle of a CVD pane says "no net delta", which
is a claim about the market rather than about the data. Everything else here is
presentation; this is the correctness rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader chooses what the lower pane shows (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the chart, **When** a reader picks a pane, **Then** that feature's series is shown and no other.
2. **Given** a pane is selected, **When** the reader picks another, **Then** the first is replaced rather than added.
3. **Given** the available panes, **When** they are listed, **Then** they are the ones this phase's data supports and no others.

---

### User Story 2 - A gap is a gap (Priority: P1)

**Why this priority**: The whole reason a pane can mislead.

**Acceptance Scenarios**:

1. **Given** points where some carry no value for the selected feature, **When** the pane is drawn, **Then** those instants are absent from the series rather than plotted at zero.
2. **Given** a feature that is zero at an instant, **When** the pane is drawn, **Then** it is plotted at zero — a real zero and a missing value must not become the same picture.
3. **Given** points that carry the feature only after some instant, **When** the pane is drawn, **Then** the line begins there rather than at the left edge.

---

### User Story 3 - Nothing to draw is stated (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a series with no points at all, **When** the pane is shown, **Then** it says so rather than rendering blank.
2. **Given** points that never carry the selected feature, **When** the pane is shown, **Then** it says the feature is unavailable — which is a different message from having no points.
3. **Given** a failed load, **When** the pane is shown, **Then** it says so and is distinguishable from both.

### Edge Cases

- **A single point.** A line of one point is a dot; it is drawn, because one reading is a reading.
- **Every value missing except one.** One point drawn, and no line joining it to nothing.
- **A feature that exists in the registry and never in the data.** Unavailable, not empty.
- **Values arriving out of order.** Sorted by instant before drawing; the API's order is not a promise the pane should depend on.
- **Two points at one instant.** The later-arriving one wins, and this is stated rather than left to the sort's stability.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The available panes MUST be exactly those this phase's data supports.
- **FR-002**: Selecting a pane MUST replace what is shown, not add to it.
- **FR-003**: A point carrying no value for the selected feature MUST be absent from the series.
- **FR-004**: A value of zero MUST be drawn as zero.
- **FR-005**: A series MUST be ordered by instant regardless of the order received.
- **FR-006**: Two points at one instant MUST resolve to the last one received.
- **FR-007**: No points at all, no values for the feature, and a failed load MUST be three distinguishable states.
- **FR-008**: The decision about what to draw MUST be testable without rendering a chart.
- **FR-009**: What the chart already draws MUST be unchanged.

### Key Entities

- **Pane**: a named feature, a label, and the series drawn for it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pane list equals the supported features; selecting one yields only its series.
- **SC-002**: Given N points of which K carry the feature, the series has K points.
- **SC-003**: A zero value appears in the series; a missing one does not.
- **SC-004**: Points supplied out of order come back ordered.
- **SC-005**: Duplicated instants collapse to one, taking the last.
- **SC-006**: The three empty-ish states produce three different messages.
- **SC-007**: Every existing chart test passes unchanged.

## Assumptions

- **The pure decision is tested; the component is not.** `lightweight-charts` needs a laid-out container and jsdom does not provide one, so a component test cannot see a line. This application already splits on that line and says why.
- **Only Phase 2's panes are built.** OI, funding, basis and liquidations belong to Phase 3's own deliverable; DEX to Phase 4. Building them here would ship panes for data those phases have not finished.
- **Pane selection is not persisted.** The deep link carries overlays and says nothing about panes; adding it changes a format other things parse.
- **How a gap looks is the plan's to decide.** A break in the line and a marked absence are both honest, and a reviewer may prefer the other.
