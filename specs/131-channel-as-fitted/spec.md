---
traces: [REQ-WP-082]
status: draft
---

# Feature Specification: The chart draws the channel as the model fitted it

**Feature Branch**: `131-channel-as-fitted`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-082]] — PRD §13.2, §27.2, §27.5.

## Context

The owner opened the chart for BTCUSDT 15m and wrote "I do not see the channel". The page does draw one: three
horizontal lines at `center_now`, `upper_now` and `lower_now`, each repeated for every bar of the loaded
history. For 800 bars that is a flat stripe across nine days, from a model that looked at the last sixty
bars, a quarter of a percent wide on an axis that a spike four days earlier stretched to 82,000-89,000. It is
there and it cannot be seen, and what is seen means nothing.

### The model, and what the page needs from it

`rolling_ols_log_price` fits `log(close) = intercept + slope · i` over the last `lookback` bars, so the
channel at bar `i` of the window is `exp(intercept + slope · i)`, and its bounds are that times fixed
`exp(low_q)` and `exp(high_q)` — constant ratios. The snapshot stores `center_now`, the bounds, `lookback`
and `slope_log_per_bar`. From those, **the whole window is exact**:
`level(i) = level_now · exp(slope · (i − last))`. Nothing is approximated; but the API does not return the
slope, and without it the page can only draw a flat line.

### As seen then

§27.5's default is AS-SEEN-THEN: the snapshot stored at the instant. A channel stored at an earlier bar must
end at that bar, not be stretched to the last bar on the chart, or the picture shows a channel that did not
exist at the moments it spans.

### What this is not

Not a forecast corridor, not a filled band (the library draws none and faking one puts edges on the chart
that do not mean what they look like), not the channel's history bar by bar, which needs a range endpoint.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The channel is a sloped band over its window (Priority: P1)

**Independent Test**: build the series for a channel with a known slope and a bar list.

**Acceptance Scenarios**:

1. **Given** a channel with lookback L and a positive slope, **Then** each of the three lines has exactly L
   points, on the L bars ending at the last bar closing at or before `as_of`, and rises across them.
2. **Then** the last point of each line equals the channel's `_now` value, and each earlier point is
   `level_now · exp(slope · −k)` for `k` bars back.
3. **Then** upper/centre and lower/centre are the same ratio at every point.
4. **Given** a channel stored at an earlier bar, **Then** the lines end there although later bars exist.
5. **Given** fewer bars than the lookback, **Then** the lines cover the bars there are.
6. **Given** a slope that is not a finite number, **Then** no lines are drawn.

---

### User Story 2 - The API says what the slope is (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a stored snapshot, **When** the channel is read, **Then** `slope_log_per_bar` equals the stored
   value, in both modes (stored and refit).
2. **Then** every field the response carried before is unchanged.

---

### User Story 3 - The chart opens on the channel (Priority: P2)

**Acceptance Scenarios**:

1. **Given** no instant in the link and a channel, **Then** the view is the last three lookbacks of bars plus
   a margin, and earlier history is reachable by scrolling.
2. **Given** an instant in the link, **Then** the chart opens there, exactly as it did.
3. **Given** no channel, **Then** the chart fits its content, as it did.

---

### User Story 4 - The lines can be seen (Priority: P2)

**Acceptance Scenarios**:

1. **Then** the centre line is solid and at least twice as thick as before, and the upper and lower lines use
   the zones' red and green.

### Edge Cases

- Missing minutes in a series: the model indexes **bars**, not clock time, and so does the drawing.
- A channel whose `as_of` is before the first bar: no lines.
- A lookback of one: a single point per line, which a line series draws as nothing; no error.
- `slope_log_per_bar` of exactly zero: a flat band over the window, which is what the model said.
- The refit view (§27.5's other mode): drawn the same way, ending at its own instant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API MUST return `slope_log_per_bar` equal to the snapshot's, and every earlier field unchanged.
- **FR-002**: The chart MUST draw each line over the bars of the window only, ending at the last bar closing at
  or before `as_of_ns`.
- **FR-003**: Each point MUST be `level_now · exp(slope_log_per_bar · (i − last))`.
- **FR-004**: A channel with no usable slope MUST draw no lines.
- **FR-005**: With no instant named and a channel present, the view MUST be the recent bars; with an instant,
  that instant; with no channel, all content.
- **FR-006**: The centre line MUST be solid and visibly heavier; upper and lower MUST use the zone colours.
- **FR-007**: No existing field, route or other layer changes.

### Key Entities

- **Channel window**: the `lookback` bars ending at the snapshot's bar.
- **Slope**: log-price change per bar of the fit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a channel of lookback 60, each line has 60 points, the last equal to its `_now`, the first
  equal to `_now · exp(−59 · slope)`.
- **SC-002**: On live BTCUSDT 15m, at least 70 % of the window's closes lie within the drawn band.
- **SC-003**: The default view contains the window and at most a few multiples of it, not the whole history.

## Assumptions

- The model indexes bars, as `np.arange(len(window))`; the drawing does the same.
- Stored snapshots carry `slope_log_per_bar` (the table has had the column since the channel tables; rows
  written before it existed read as 0.0).
- The chart library autoscales to the visible range, so a recent view drops an old spike from the axis.
