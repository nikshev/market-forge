---
id: OUT-2026-10-04-plan-lower-pane-chart
step: plan
records: [REQ-WP-092]
commit: null
---

## What was decided

- **Pure decisions in `paneChart.ts`** (`alignToBars`, `runsOf`, volume colours); **`PaneChart.tsx`** is the second
  chart with a whitespace backbone, one line series per run, a DOM legend, a zero line, `minimumWidth` and two-way
  synchronisation with a loop guard.
- **`Chart` hands out `{ api, candles() }`** through an optional `onReady`; `FlowPane` draws the pane chart with it and
  the SVG without.
- **One line series per run for CVD**, not whitespace between runs in one series (a whitespace entry takes an axis
  slot the main chart does not have).

## What was rejected

- v5 panes; more series on the main chart's own scale; a singleton or context for the handle; debouncing the sync.

## What is still open

- Resize and phone rotation rely on `autoSize` and are checked by screenshots at two widths, not by a unit test.
