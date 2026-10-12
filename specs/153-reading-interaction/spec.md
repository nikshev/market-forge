---
traces: [REQ-WP-101]
status: draft
---

# Feature Specification: A chart is read, not operated

**Input**: [[REQ-WP-101]] -- owner's report 2026-10-12. Builds on [[REQ-WP-092]].

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scrolling the page does not move the chart (P1)

**Independent Test**: the options both charts are created with turn the wheel off for zoom and scroll.

**Acceptance Scenarios**:

1. **Given** the pointer over the chart, **When** the wheel turns, **Then** the page scrolls and the chart's range is unchanged.
2. **Given** a pane under the chart, **Then** it has the same behaviour, because it follows the chart's range.

### User Story 2 - The price scale is the data's (P2)

**Acceptance Scenarios**:

1. **Given** any bars, **Then** the price axis is on auto-fit and a drag on it does not change that.
2. **Given** the candles, **Then** they use the plot's height with 8 % margins instead of the library's 20 % and 10 %.

### Edge Cases

- A reader who wants to zoom drags the time axis or pinches; the wheel no longer does it.
