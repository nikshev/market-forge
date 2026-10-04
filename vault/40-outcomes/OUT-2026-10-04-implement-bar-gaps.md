---
id: OUT-2026-10-04-implement-bar-gaps
step: implement
records: [REQ-WP-086]
commit: null
---

## What was done

A missing bar is visibly missing, on the **live stack**. A gap is found from two consecutive bars' own windows and is
marked on the chart with one amber square at the first bar after the hole, whose text states how many bars are missing; a
notice under the chart lists each hole in words with its UTC span; the Volume pane and a CVD run that starts at a gap carry
the same marker (no text, so they do not pile up in a pane that short). The axis is unchanged.

- `gaps.ts` (pure): `findGaps`, `gapMarkers`, `describeGap`, `noticeLines`.
- `Chart.tsx`: the gap markers join the single `setMarkers` call, sorted by time.
- `GapNotice.tsx` + `App.tsx`: the notice (role `status`, named "Gaps in the bars"; five lines, the rest counted).
- `PaneChart.tsx`: markers on the histogram at bars with a value, and on a CVD run whose first point is at a gap marker's time.

**RED first.** Four files against unchanged source:

    Failed to resolve import "../gaps" / "../GapNotice"          (two files)
    Failed Tests 6: chartGapMarkers (no gap marker in the call), paneChartGaps (no markers on the pane's series)

**After.** Web 471/471 (**446 existing, none edited**, plus 25 new); `make lint`, `make typecheck`, `make web-typecheck`
clean; `make web-build` green. **Bundle gzip** 166,199 B -> 166,906 B (+707 B).

## Edits to existing tests

None. (One of my own new tests had a wrong date constant, a day out; the implementation was right and the test now builds the
date from `Date.UTC`.)

## What looking at the live screenshots showed

`docs/ui/gaps-{eth1h,btc15m}-{light,dark}.png`, **live data**, as the holes stood on 2026-10-04:

1. **ETHUSDT 1h:** an amber "148 missing" square right after the hole in the middle of the chart, three smaller ones
   ("2", "1", "2 missing"), and the notice reading "148 bars missing, 26.09 07:00 to 02.10 11:00" -- the figure measured
   earlier from the API. The hole that the candles hid is now the most visible thing on the chart.
2. **BTCUSDT 15m:** the notice lists the five most recent and counts "and 2 more", and its biggest hole (397 bars, 28.09 07:45
   to 02.10 11:00) is outside the visible range: the notice is how a reader learns it exists.
3. **The pane, first version, was cluttered:** the markers' texts lay on top of each other in a pane that short. The pane's
   markers are now squares without text; the count is on the chart and in the notice.
4. The Volume pane's squares sit exactly under the chart's.
5. **Left as observed:** a marker's label is clipped at the chart's left edge when the marker is on the first visible bar.

## What was decided

- The hole is **marked, not stretched**: the pane lines up with the chart by index and the visible range and channel window are
  indices; a time-true axis would let a 397-slot hole swallow the view and change all of them. It is a decision of its own.
- The marker states how many; the notice states how many and over what span. The requirement's acceptance was amended in the
  spec step to say so: a marker is a few characters and cannot carry a span.

## What is still open

- A time-true axis; what the detector and the channel do across a hole ([[REQ-WP-087]], awaiting the owner's decision);
  freshness of the last bar ([[REQ-WP-090]]).
