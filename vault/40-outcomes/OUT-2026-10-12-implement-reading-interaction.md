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

## What is still open

- The deployed check (the wheel scrolls the page over the new build) is the last acceptance line; the web image is rebuilt
  after the commit.
