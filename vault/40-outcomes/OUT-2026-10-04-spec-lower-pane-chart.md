---
id: OUT-2026-10-04-spec-lower-pane-chart
step: spec
records: [REQ-WP-092]
commit: null
---

## What was decided

- **A second chart instance, synchronised**, not a v5 upgrade: the installed 4.2.3 typings have the visible-range and
  crosshair synchronisation, `minimumWidth` and whitespace data; v5's panes would be cleaner but change every call the
  chart makes, which is a decision of its own.
- **Alignment is by bar and is the whole feature.** The library's time axis is an index over the union of the series'
  times, so two charts line up only if they hold the same sequence of times: a bar without a value is whitespace, and a
  value goes to the bar whose window contains its instant (the later wins), never to a slot of its own.
- **Facts read that the owner's complaint implied but did not say:** the pane is 720 px wide on a 1,150 px chart; the
  Volume pane was placed by `open_time_ns` while the candles sit at `close_time_ns`; and the pane's axis is time-true
  while the candles' is an index axis, so a hole shows in one and not the other.
- The SVG stays as the fallback, which is also what the existing tests exercise.

## What is still open

- How a hole in the bars is shown on either chart ([[REQ-WP-086]]); the pane follows whatever the main chart does.
- Volume as a histogram at the foot of the main chart: named in the requirement as optional, not built here.
