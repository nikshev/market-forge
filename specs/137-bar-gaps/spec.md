---
traces: [REQ-WP-086]
status: draft
---

# Feature Specification: A missing bar is visibly missing

**Feature Branch**: `137-bar-gaps`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-086]] — PRD §32; the owner's direction of 2026-10-04.

## Context

The chart plots bars one after another on an index axis, so a hole in the series is drawn as no hole at all. Measured on
2026-10-04 against the running API (hourly bars, the latest 500): ETHUSDT 153 missing bars (one hole of 148 hours),
BTCUSDT 109, SOLUSDT 154; BTCUSDT 15m has one of 397 slots. Candles a week apart sit side by side, with the channel, the
extrema and the lower panes drawn across them.

### Facts read from the code, which decide the design

- A `BarOut` carries `open_time_ns` and `close_time_ns`; its window length is its own timeframe, so a missing bar is
  decided from the bars alone: two consecutive bars whose gap `next.open - prev.close` is more than zero.
- The chart sets its marks in **one** `setMarkers` call (`Chart.tsx`: the signal's, then the extrema's), because the
  library replaces the whole set; a gap mark must join that list and keep the list ordered by time.
- The main chart's axis stays an index axis (the lower pane lines up with it by index, [[REQ-WP-092]]); making the axis
  time-true would give a 397-slot hole its width but change every index-based rule (the visible range, the channel
  window). That is not decided here: the gap is **marked**, not stretched.
- A series marker can carry a shape, a colour and a few characters of text, not a span; a span needs words.
- A bar with volume `0` is a bar that exists; a missing bar is a bar that does not. They must never look alike.

### What this is not

Not a time-true axis, not backfill, and not what the detector or the channel do across a hole ([[REQ-WP-087]]).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The gap is marked where it is (Priority: P1)

**Independent Test**: give the chart bars with a hole and read the marks handed to the library.

**Acceptance Scenarios**:

1. **Given** bars with N missing bars between two present ones, **Then** the chart carries one marker at the first bar
   after the hole, in its own colour and shape, whose text states N.
2. **Given** contiguous bars, **Then** no gap marker exists.
3. **Given** two holes in one series, **Then** two markers; **given** a hole of exactly one bar, **Then** a marker stating 1.
4. **Given** a bar present with volume `0`, **Then** no marker.
5. **Given** a signal marker or extremum markers at other bars, **Then** all marks stay in one call, ordered by time, and a
   gap marker at the same bar as another mark does not hide it.

---

### User Story 2 - The gap is said in words (Priority: P1)

**Acceptance Scenarios**:

1. **Given** one or more holes among the loaded bars, **Then** a notice below the chart (role `status`, named "Gaps in the
   bars") lists each hole with how many bars are missing and the span it covers, in UTC, most recent first.
2. **Given** more than five holes, **Then** the five most recent are listed and the rest are counted.
3. **Given** no holes, **Then** there is no notice.
4. **Then** the notice's text is the same facts the markers carry, so a reader using a screen reader has them.

---

### User Story 3 - The lower pane does not contradict it (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the Volume pane (bars), **Then** the same gap markers are set on its series at the bars that carry a value.
2. **Given** the CVD pane, **Then** its lines are already one per run and break at the gap; a marker is set on the first
   point of each run that starts at a time gap.

---

### User Story 4 - Looked at (Priority: P2)

**Acceptance Scenarios**:

1. **Then** screenshots of ETHUSDT 1h (the 148-bar hole) and BTCUSDT 15m on the live stack, light and dark, are kept
   under `docs/ui/` and each is looked at.

### Edge Cases

- A hole at the very start or end of the loaded range is not a hole (nothing is on one side of it).
- Bars not in time order: sorted by `open_time_ns` first.
- A corrected bar with the same `open_time_ns`: not a gap (a gap needs a positive distance).
- A forming (last) bar: counts like any other bar for what lies before it.
- A series whose last bar is old is stale, not holed: freshness is [[REQ-WP-090]]'s, and nothing is marked after the last bar.
- A hole smaller than a bar is not possible on aligned bars; a misaligned series (the gap not a whole number of bars) reports
  the count rounded and the span exactly.
- Hundreds of holes: the notice is capped, the markers are all set (they are cheap) but only those in range are visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A gap MUST be found from the bars alone: two consecutive bars (by `open_time_ns`) with `next.open_time_ns > prev.close_time_ns`; its size MUST be the missing bars, `(next.open - prev.close) / window`, rounded.
- **FR-002**: The chart MUST carry one marker per gap at the first bar after it, whose text states the number of missing bars, in the same single `setMarkers` call as the other marks, in time order.
- **FR-003**: A bar that exists, whatever its volume, MUST NOT produce a gap or a marker.
- **FR-004**: A notice MUST list each gap with its number of missing bars and its span, most recent first, capped at five with the rest counted, and MUST be absent with no gaps.
- **FR-005**: The Volume pane MUST carry the gap markers at the bars that have a value, and a CVD run that starts at a time gap MUST carry one on its first point.
- **FR-006**: The axis, the visible range and every index-based rule MUST be unchanged.
- **FR-007**: Screenshots of ETHUSDT 1h and BTCUSDT 15m, live, light and dark, MUST be kept under `docs/ui/`.

### Key Entities

- **Gap**: `{ afterCloseNs, beforeOpenNs, missing }` between two consecutive bars.

## Success Criteria *(mandatory)*

- **SC-001**: For bars 0,1,2,6,7 of a 60-second series, one gap with `missing` 3; for 0,1,3 one gap of 1; for two holes two gaps.
- **SC-002**: With a signal at bar 6 and a gap marker at bar 6, both marks reach the library, ordered.
- **SC-003**: The notice for ETHUSDT 1h's real hole reads 148 bars and the correct UTC span.
- **SC-004**: The existing web tests pass with only the edits the outcome note lists.
- **SC-005**: The live screenshots exist and were looked at.

## Assumptions

- The marker's colour and shape are this feature's own (amber square) and do not collide with the signal or extrema marks.
- The live screenshots are of the holes as they stood on 2026-10-04 (ETHUSDT 1h: 148 bars); a later backfill may close them, which is why the tests use fixtures.
- Dates in the notice are UTC and written `DD.MM HH:mm`, as the owner's own examples are.
