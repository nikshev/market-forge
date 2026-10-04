---
id: OUT-2026-10-04-plan-bar-gaps
step: plan
records: [REQ-WP-086]
commit: null
---

## What was decided

- A pure `gaps.ts` (`findGaps`, `gapMarkers`, `describeGap`, `noticeLines`); the chart merges the gap markers into its single
  `setMarkers` call, sorted by time; a `GapNotice` under the chart; the pane marks its histogram and the first point of a CVD
  run whose time matches a gap marker.
- The notice is capped at five lines with the rest counted: a series can carry hundreds of holes.

## What was rejected

- A time-true axis; a DOM overlay band (re-computed on every pan and zoom); packing count and span into the marker text.

## What is still open

- Nothing blocking.
