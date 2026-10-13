---
id: OUT-2026-10-12-implement-reading-interaction
step: implement
records: [REQ-WP-101]
commit: null
---

## What was done

Reproduced the owner's report with a headless browser against the running stack: the wheel over the chart zoomed the time axis
(the candles squeezed into the left of the plot) and the page did not scroll. `READING_INTERACTION` and `PLOT_MARGINS` in
`paneChart.ts` are now what the main chart and every pane are created with.

## Evidence

**RED first**: five tests on the options failed (nothing exported them). **GREEN**: they pass; the whole web suite (530 tests)
and `tsc --noEmit` pass.

## What was decided / found

- The Y scale was already auto-fitting; what the owner saw was a range wider than the candles (default margins 20 %/10 %) and
  the price axis being draggable. Both are settled by options rather than by code that fights the library.
- Zoom by wheel is removed on purpose: it is the same gesture as scrolling the page. Pinch and dragging the time axis remain.

## Deployed run (2026-10-12)

The web image was rebuilt; in a headless browser against it the same six wheel ticks over the chart moved the page
(`scrollY` 0 -> 210), the chart kept its full width, and the panes came into view with the chart's time axis unchanged.

## What is still open

- Nothing in the repository: the deployed check was made.

## Correction (2026-10-13)

The owner reported after the live feed shipped: "now it does not scale at all, neither horizontally nor vertically." That was this
requirement's doing: it had turned the wheel and the price-axis drag off to stop the page being captured by the chart, and the chart
could no longer be scaled. The constant is now `CHART_INTERACTION` and gives the reader the scaling (wheel zoom, price-axis drag, double
click to reset, pinch); the vitest file and the pytest artifact test assert that instead.

Measured in a headless browser on the rebuilt web image: five wheel ticks zoomed the time axis from ~7 h to ~5 h of 1m candles and the
price axis rescaled with it (80750-84250 for the candles shown); a drag on the price axis changed its range (81200-83800); a double click
restored the auto-fit. The page does not scroll while the pointer is over a chart -- the usual trade of a chart that zooms with the wheel --
and scrolls everywhere else.

The lesson, for the next requirement of this kind: the owner's report was of a symptom (the axis moved by itself); the first fix removed
the capability instead of the cause. What did squeeze the axis unasked was never isolated; if it recurs it will be with the wheel enabled,
which is what to reproduce.
