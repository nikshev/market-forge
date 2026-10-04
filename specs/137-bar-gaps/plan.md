# Implementation Plan: A missing bar is visibly missing

**Branch**: `137-bar-gaps` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

`gaps.ts` (pure): `findGaps(bars)`, `gapMarkers(gaps, bars)`, `describeGap(gap)`, `noticeLines(gaps)`. `Chart` merges the gap
markers into its single marker list. `GapNotice.tsx` renders the notice under the chart. `PaneChart` sets the same markers
on its histogram and on the first point of a CVD run that starts at a gap. No change to the axis.

## What planning measured

- `Chart.tsx` builds `marks` (the signal's, then `extremumMarkers`) and calls `candlestick.setMarkers(marks)` only when it
  is non-empty; the library replaces the whole set, and expects it ordered by time.
- `BarOut` has `open_time_ns` and `close_time_ns`; there is no timeframe field, so the window is `close - open`.
- The live holes this must show: ETHUSDT 1h `09-26 06:00 -> 10-02 11:00` (148), three of 1-2; BTCUSDT 15m one of 397 slots.
- `PaneChart` already holds `bars`; its series are created per pane and replaced on change.

## Decisions, and what each rejected

**D1. Mark, do not stretch.** A marker at the first bar after the hole plus a notice in words. Rejected: a time-true axis
(true width for the hole, but every index rule changes and a 397-slot hole would swallow the view); a vertical band drawn as
a DOM overlay (follows pan and zoom only by re-computing coordinates on every change; a second piece to keep in step).

**D2. The span is in the notice, the count in the marker.** A marker carries a few characters and no span. Rejected:
packing both into the marker text (illegible at the density of a month of 15m bars).

**D3. Gap found from the bars' own windows**, not from a timeframe passed in: it cannot disagree with the bars. Rejected:
using the selected timeframe (a corrected or mixed series would misreport).

**D4. Marks stay in one call, merged and sorted by time**, and a gap marker never replaces another at the same time.

**D5. The notice is capped at five lines** with the rest counted: a series can carry hundreds of holes.

**D6. The pane gets the markers on the series that carry a value at that bar** (the histogram; the first point of a CVD run).
A CVD run is marked only if its first point is at a time a gap marker is at: the pane intersects the gap marker times with
the run's first point, not the run number, because a run also starts after a trade-id break, where nothing is missing
from the bars and no gap marker belongs. Rejected: markers on the whitespace backbone (markers attach to points with values).

## Tests (written first)

vitest, pure: `findGaps` (SC-001, a hole at the ends is not a hole, unsorted input, a corrected bar, a misaligned series,
volume zero), `gapMarkers`, `describeGap`/`noticeLines` (span in UTC, cap and count). With the library replaced: the chart's
marks include the gap marker in one ordered call alongside a signal marker; none for contiguous bars; the pane's histogram
and CVD run markers. Component: `GapNotice` (role `status` named "Gaps in the bars", lists, capped, absent). Python: the
screenshots exist, the modules trace.

## Constitution Check

I: nothing looks beyond the loaded bars. III: nothing is rewritten. VII: display only. XIV: traced. No violations.

## Risks

- Several marks at one bar (a signal and a gap): all must reach the library; ordered, with distinct ids.
- A very large number of gaps makes many markers: cheap, and only those in range are drawn.

## Project Structure

```text
apps/web/src/gaps.ts            findGaps, gapMarkers, describeGap, noticeLines (new, pure)
apps/web/src/GapNotice.tsx      the notice (new)
apps/web/src/Chart.tsx          merge the gap markers into the one setMarkers call
apps/web/src/PaneChart.tsx      markers on the histogram and on a run's first point
apps/web/src/App.tsx            render the notice under the chart
specs/137-bar-gaps/screenshots.mjs
tests/unit/web/test_bar_gaps_artifacts.py
```
