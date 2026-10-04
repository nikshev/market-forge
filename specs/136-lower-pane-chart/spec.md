---
traces: [REQ-WP-092]
status: draft
---

# Feature Specification: The lower pane is a chart on the main chart's own time axis

**Feature Branch**: `136-lower-pane-chart`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-092]] — PRD §27.3; the owner's direction of 2026-10-04.

## Context

The Volume and CVD panes under the chart are a 720 x 120 px hand-drawn SVG with its own time scale, no axis, no
name, no last value and no crosshair. The owner could not tell what it was and asked for the data on the chart or a
proper chart below with a matching timeline.

### Facts read from the code, which decide the design

- The main chart (`Chart.tsx`) is one `createChart` per scheme and palette, with one data effect that creates the
  candle series and the channel lines **every time its data changes** and removes them in its cleanup. The candles sit
  at each bar's **`close_time_ns`** in seconds (`series.ts`); the volume pane used `open_time_ns`.
- `lightweight-charts` 4.2.3 (installed) has what a two-chart stack needs: `timeScale().subscribeVisibleLogicalRangeChange`
  and `setVisibleLogicalRange`, `subscribeCrosshairMove` and `setCrosshairPosition`, a price scale `minimumWidth`,
  histogram and line series, whitespace data, and series `title`. No native panes (that is v5), so the pane is a
  **second chart instance**, two-way synchronised.
- The library's time axis is **an index axis over the union of all series' times**: a logical index means "the n-th
  distinct time". Two charts line up only if they hold the **same sequence of times**. A bar with no value in a pane
  must therefore be a whitespace point (a time with no value), not an absent point; and a series holding only its own
  times does not disturb the sequence if another series of the same chart holds all of them.
- Feature points are stored at the instant they were computed; the flow features sit at the bar's close, but other
  features' instants need not equal a bar time. A point that is not at a bar's time would add a slot to the pane's
  axis and shift every index after it.
- `FlowPane` and its tests render an SVG (`role="img"`, name `<feature> over N point(s)`); in jsdom `lightweight-charts`
  cannot lay out, so those tests cannot see a real chart. The existing tests are the regression contract.
- The page mounts `<Chart>` and `<FlowPane>` as siblings; the pane has no handle to the main chart.

### Alignment is by bar, and a value belongs to the bar that contains its instant

A pane value is shown at the **candle of the bar whose window `(open, close]` contains the value's instant**: a value stamped
exactly at a bar's close is that bar's (the flow features are stamped at the close of the bar they describe, and would
otherwise land on the next one); two values in one bar show the later. Values are never moved to a bar that did not exist and a bar
without a value is a gap. This is a display rule: nothing computed changes, and nothing looks later than the bar.

### What this is not

Not a v5 upgrade, not a change to which data a pane has, not the marking of holes in the bars ([[REQ-WP-086]]); but
the pane must not disagree with the main chart about a hole: both are on the main chart's axis, so whatever it does the
pane does.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The pane is on the chart's time axis (Priority: P1)

**Independent Test**: build the pane's data from bars and a series and read the times handed to the library.

**Acceptance Scenarios**:

1. **Given** bars and a feature series, **Then** the pane's series holds one entry per bar, at that bar's candle time
   (`close_time_ns` seconds); a bar without a value is a whitespace entry; no entry exists at a time with no bar.
2. **Given** a feature point whose instant is inside a bar but not at its close, **Then** it is shown at that bar's
   time; two points in one bar show the later one.
3. **Given** the main chart is zoomed or panned, **Then** the pane's visible logical range becomes the same, and the
   reverse; a change that the other chart made does not echo back (no loop).
4. **Given** the crosshair moves over either chart, **Then** it appears at the same bar on the other.
5. **Given** the pane and the main chart, **Then** their right price scales have the same minimum width, and the
   pane's container has the same horizontal inset as the main chart's, so the plot areas line up.
6. **Given** the pane chart is created (on first use, or again after a change of scheme or palette), **Then** it
   takes the main chart's current visible range at once; it does not start from its own.
7. **Given** the `candles` layer is off, **Then** the main chart still holds the whole sequence of bar times (as
   whitespace), so the pane still lines up with it.

---

### User Story 2 - A pane that can be read (Priority: P1)

**Acceptance Scenarios**:

1. **Then** the pane shows its title ("Volume", "CVD (base)", ...) and its last value, and a value axis with labels.
2. **Given** the CVD pane, **Then** a zero line is visible and the series is one line **per run** (`cvd_run`), so no
   line joins two runs.
3. **Given** the Volume pane, **Then** it is bars coloured by the candle's direction (close at or above open: up).
4. **Given** any other feature pane with data, **Then** it is a line on the same terms.
5. **Then** light and dark follow the page's palette, and at 390 px the pane is as wide as the chart.

---

### User Story 3 - Nothing the reader relies on changes (Priority: P1)

**Acceptance Scenarios**:

1. **Then** the pane group, one button per pane, the disabled "no data" buttons, the "No pane has data" and failure
   messages keep their roles and names ([[REQ-WP-084]], [[REQ-WP-085]]).
2. **Then** the pane's chart is an element with `role="img"` named `<feature> over N point(s)`, as the SVG was.
3. **Given** no handle to the main chart (a page without it, or a test), **Then** the pane falls back to the SVG it is
   today, so a missing chart is never an empty pane.
4. **Given** a change of selected pane, scheme or data, **Then** the pane's series are replaced without piling up
   (as the main chart's are) and the visible range the reader chose is kept.

---

### User Story 4 - Looked at (Priority: P2)

**Acceptance Scenarios**:

1. **Then** screenshots of the Volume and the CVD panes on the live stack, light and dark, at 1280 px and 390 px, are
   kept under `docs/ui/` and each is looked at; what looking showed is recorded.

### Edge Cases

- No bars: no pane chart (the pane says "no data" as before).
- One bar: one entry, the axes degenerate gracefully.
- A series with all values equal: drawn at one level, axis non-degenerate.
- A forming bar (no volume yet): a whitespace entry, not zero.
- A value at the exact boundary between two bars: the earlier bar (a window is `(open, close]`), because a value stamped
  at a bar's close describes that bar; this differs from the trade-to-bar rule `[open, close)` on purpose, and a test pins both.
- Resizing and phone rotation: the pane follows the container's width; the price-scale widths stay equal.
- A bar present in the main chart's candles but missing from the pane's data: whitespace, so indices stay aligned.
- Unmount order: removing the pane chart after the main chart is gone must not throw.
- Layers: with `candles` off the main chart's own series may hold fewer times; alignment must not depend on that.
- A synchronisation echo (`setVisibleLogicalRange` firing the other's subscription) must not loop.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The lower pane MUST be a chart of the same library, below the main chart, whose series hold exactly the main chart's sequence of bar times (a whitespace entry where a bar has no value), at each bar's `close_time_ns` seconds.
- **FR-002**: A value MUST be shown at the bar whose window `(open, close]` contains its instant, the later of two in one bar winning; no entry MAY be created at a time without a bar.
- **FR-003**: The visible logical range and the crosshair MUST be synchronised both ways between the main chart and the pane, without feedback loops.
- **FR-004**: Both charts' right price scales MUST have the same minimum width and the two containers the same horizontal inset; a new pane chart MUST take the main chart's current visible range.
- **FR-004a**: The main chart MUST hold the whole sequence of bar times whatever layers are on (whitespace where its candles are off), so that index alignment never depends on a layer.
- **FR-005**: The pane MUST show a title, the last value and a labelled value axis; the CVD pane MUST show a zero line and one line series per run; the Volume pane MUST be bars coloured by candle direction.
- **FR-006**: The pane's roles and names, the pane selector and the "no data" and failure rules MUST be unchanged, and the pane's chart MUST be an element with `role="img"` named `<feature> over N point(s)`.
- **FR-007**: Without a handle to the main chart the pane MUST draw the SVG it draws today.
- **FR-008**: Series MUST be replaced, not accumulated, on a change of data, pane, scheme or palette, and removing the pane after the main chart MUST NOT throw.
- **FR-009**: Screenshots of the Volume and CVD panes, live, light and dark, 1280 px and 390 px, MUST be kept under `docs/ui/`.

### Key Entities

- **Chart handle**: what the main chart gives out: its chart API and a way to read its current candle series.
- **Pane series**: the aligned data: for each bar time, a value or whitespace.

## Success Criteria *(mandatory)*

- **SC-001**: With 12 bars (one forming) and a series with values at 10 of them, the pane's series holds 12 entries at the 12 candle times, 10 with values and 2 whitespace.
- **SC-002**: A point at 30 s into a 60 s bar is shown at that bar's close time; two points in one bar show the later value.
- **SC-003**: After a visible-range change on the main chart the pane's range equals it; after one on the pane, the main chart's equals it; no more than one call each way.
- **SC-004**: At 1280 px and 390 px the pane's plot area edges equal the chart's (measured in a browser).
- **SC-005**: The existing web tests pass with only the edits each outcome note lists.
- **SC-006**: The live screenshots exist and were looked at.

## Assumptions

- The pane keeps one chart instance per selected pane; switching pane replaces its series, it does not create a second chart.
- The main chart's index axis stays as it is; how a hole in the bars is shown is [[REQ-WP-086]]'s.
- Pane height is fixed (about 160 px); it is not user-resizable.
