---
id: OUT-2026-10-04-implement-lower-pane-chart
step: implement
records: [REQ-WP-092]
commit: null
---

## What was done

The lower pane is a chart of the same library under the main one, on the main chart's own time axis: Volume as bars
coloured by the candle's direction, CVD as one line per run with a zero line, any other feature as a line; a title and
last value, a labelled value axis, a shared crosshair and a shared visible range. **Live on the running stack** (BTCUSDT 15m).

- `paneChart.ts` (pure): `alignToBars`, `lineRuns`, `volumeBars`, `backbone`, `paneView`, `PRICE_SCALE_WIDTH`.
- `PaneChart.tsx`: the second chart, a whitespace backbone holding every bar time, the pane's series, a DOM legend,
  two-way synchronisation (the main chart leads), crosshair sync, cleanup that survives the main chart going first.
- `Chart.tsx`: an optional `onReady` handle `{ api, candles() }`; the same price-scale minimum width; with the candles
  layer off, a whitespace entry per bar time so the axis never depends on a layer.
- `FlowPane.tsx`: `PaneChart` with a handle, today's SVG without; `App.tsx` keeps the handle and passes it down.

**RED first.** Five new test files written against unchanged source:

    Failed to resolve import "../paneChart" / "../PaneChart"   (four files)
    Unable to find an element by: [data-testid="pane-chart"]    (flowPaneChart, two cases)

**After:** web 446/446 (**411 existing, none edited**, plus 35 new); `make lint`, `make typecheck`,
`make web-typecheck` clean; `make web-build` green. **Bundle gzip** 164,428 B -> 166,199 B (+1,771 B).

## What looking at the live screenshots found (and a bug no test would have)

Eight screenshots, `docs/ui/pane-{volume,cvd}-{light,dark}-{desktop,phone}.png`, **live data**:

1. **A synchronisation feedback loop.** The first screenshot showed the *main* chart wrong: the first 60 bars of a
   500-bar series with an empty left edge and no channel. Instrumenting the page showed why. Replacing the pane's
   series makes the library reset the pane's visible range for a moment (to `{-65, 60}`, the empty chart's), and the
   pane reported that to the main chart, which obediently moved there. Fixed by making the main chart lead: a
   pane range drives the main chart only while the reader's pointer is on the pane; a range the pane reports by itself
   puts the pane back to the chart's. Two tests pin it. No unit test with a fake library would have produced the
   bug, because the fake does not reset its range on `removeSeries`.
2. **The price-scale minimum was too small.** 72 px against a natural width of about 80 for the main chart's labels left
   the pane's plot area ten pixels wider than the chart's. 88 px for both.
3. **The boundary rule had to be decided.** A trade at a bar's boundary belongs to the later bar (`[open, close)`); a
   *value* stamped at a bar's close, as the flow features are, belongs to that bar (`(open, close]`). Both rules are pinned.
4. Measured in a browser at 1280 px and 390 px: the pane's container and the chart's have **identical left and right
   edges in all eight screenshots**, and the time labels of the pane sit under the chart's.
5. The CVD line is visibly **broken** where the bars have a gap (a missing bar at about 18:00), and Volume's bars sit
   under their candles.
6. **Left as observed, not fixed:** the topmost value-axis label of the CVD pane touches the pane's edge; the time labels
   appear twice (under the chart and under the pane); on a phone the candles are thin outlines (unchanged).

## What was decided

- The main chart leads; the pane follows. A range change on the pane is the reader's only when the pointer is on it.
- The SVG remains as the fallback and as what the existing pane tests exercise.
- The index axis stays: a hole in the bars is hidden on both charts alike, which is what keeps them aligned. Marking
  it is [[REQ-WP-086]].

## What is still open

- Resize and rotation rely on `autoSize` and the two screenshot widths, not on a test.
- The optional volume histogram at the foot of the main chart was not built.
