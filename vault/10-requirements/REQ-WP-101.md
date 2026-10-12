---
id: REQ-WP-101
title: "A chart is read, not operated: the wheel scrolls the page, and the price axis stays on its auto-fit"
type: work-package
prd_ref: "§27.2, §27.3; owner's report 2026-10-12"
prd_lines: "4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-092, REQ-WP-080]
tags: [web, chart, interaction]
hard_gated: false
---

## Requirement

The owner reported on 2026-10-12 that the chart's X axis "squeezes and stretches" and that the Y scale is wrong.
Reproduced in a browser against the running stack: with the pointer over the chart, **the mouse wheel zoomed the time axis
and the page did not scroll** (`scrollY` stayed 0 after six wheel ticks), so a reader moving down to the panes squeezed and
stretched the candles instead -- and the pane under the chart, kept on the same range, moved with it. The price scale
stayed at the range of the data while the candles used a part of the plot's height, and a drag on the price axis, which
the library lets switch its auto-fit off, left a scale nobody chose.

1. The main chart and every pane are created **without wheel zoom or wheel scroll**, without dragging the price axis and
   without vertical touch drag; pinch, dragging the plot and dragging along the time axis remain.
2. The main chart's price scale is explicitly on auto-fit, with margins (8 % above and below) that let the candles fill
   the plot.

## Acceptance

- The options each chart is created with carry the above (tests on what the library is handed; it cannot be drawn in jsdom).
- In a browser against the running stack the wheel over the chart scrolls the page, and the chart's range does not change.

## Trace

<!-- trace:begin -->
<!-- trace:end -->
