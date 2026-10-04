---
id: OUT-2026-10-04-tasks-lower-pane-chart
step: tasks
records: [REQ-WP-092]
commit: null
---

## What was done

15 tasks, tests first. `speckit-analyze` found two holes that would have defeated the feature's one purpose, one
inconsistency and one gap; all fixed in the artifacts before implementation.

## What the analysis found, and how it was resolved

- **F1 (HIGH): alignment depended on a layer.** The main chart's time axis is whatever its series hold; with the
  `candles` layer off its candle series was `setData([])` and only the channel lines defined the axis, so the pane's
  indices would drift from the chart's. The main chart now always holds the whole bar sequence (whitespace where its
  candles are off): D9, FR-004a, T006, T011.
- **F2 (HIGH): the pane's starting range was unspecified.** The main chart has already set its range when the pane is
  created, so a pane starting at its own would sit apart until the reader moved something. A new pane chart adopts the
  main chart's range at creation (D10, scenario 6, T004).
- **F3 (MEDIUM): different insets.** The main chart is inside a `Paper` with padding and a border; the pane was not, so
  equal price-scale widths would not have meant equal plot areas and SC-004 would have failed late. The pane gets the
  same inset (D11, FR-004).
- **F4 (LOW): resize and rotation** have no unit test: covered by `autoSize` and screenshots at 1280 px and 390 px.

## What is still open

- Nothing blocking implementation.
