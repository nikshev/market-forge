# Implementation Plan: The lower pane is a chart on the main chart's own time axis

**Branch**: `136-lower-pane-chart` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

`paneChart.ts` holds the pure decisions: `alignToBars` (a value per bar time, whitespace where none, a value at the bar
containing its instant) and `runsOf` (one line per `cvd_run`). `PaneChart.tsx` is a second `createChart` below the main
one: a whitespace "backbone" series holding every bar time, the pane's series on top, a DOM legend (title, last value),
`minimumWidth` on the price scale, and two-way sync of the visible logical range and the crosshair with a loop guard.
`Chart` gains an optional `onReady` that hands out `{ api, candles() }`; `App` keeps it in state and gives it to
`FlowPane`, which draws a `PaneChart` when it has the handle and today's SVG when it does not.

## What planning measured

- The 4.2.3 typings have `setCrosshairPosition(price, time, series)`, `clearCrosshairPosition()`,
  `subscribeCrosshairMove`, `subscribeVisibleLogicalRangeChange`, `setVisibleLogicalRange`, price scale
  `minimumWidth`, `addHistogramSeries`, `addLineSeries`, whitespace data and series `title`.
- The candles are at `toSeconds(bar.close_time_ns)`; the main chart's data effect creates and removes its series on
  every data change, so the candle series object changes: the handle exposes a getter, not the object.
- `Chart.tsx`'s existing tests (`chartSeriesCleanup`, `chartCandidates`) mock `createChart` with only
  `addCandlestickSeries`, `addLineSeries`, `removeSeries`, `timeScale().{fitContent,setVisibleLogicalRange}` and `remove`;
  an optional `onReady` and extra `createChart` options do not touch them.
- App-level tests mock `../Chart`, which never calls `onReady`, so the pane falls back to the SVG there: their `img`
  queries keep working. `FlowPane`'s own tests pass no handle, so the SVG path is what they test.
- The volume series used `open_time_ns` (REQ-WP-085); the pane chart uses the bar's `close_time_ns`, so `volumeSeries`
  keeps its tested contract and `alignToBars` places by the bar's window, which makes the choice of instant moot.

## Decisions, and what each rejected

**D1. A second chart instance, synchronised.** Rejected: upgrading to v5 for native panes (a change to every call the
chart makes, a decision of its own); more series on the main chart with scale margins (CVD and volume have different
scales and would crowd the candles; kept only as the optional volume histogram, not built here).

**D2. A whitespace backbone series holds every bar time** in the pane chart. The library's axis is the union of the
series' times, so a series with only its own times (a CVD run) would leave slots missing and shift every index.
Rejected: padding each series with whitespace (many large arrays; the backbone is one).

**D3. One line series per run for CVD.** Rejected: whitespace between runs in one series (it takes an axis slot the main
chart does not have, so every index after it shifts).

**D4. A value belongs to the bar whose window `(open, close]` contains its instant** (a value at a bar's close is that bar's: the
flow rows are stamped there). Rejected: dropping values not at a bar time
(loses real data); creating a slot for them (breaks alignment).

**D5. The handle is `{ api, candles() }`, delivered by an optional `onReady` and cleared on unmount.** Rejected: a global or
context singleton (a second chart on a page would collide); the pane owning the main chart (inverts the structure).

**D6. A loop guard by identity**: a range change that originated from the other chart's `setVisibleLogicalRange` is not
sent back (a flag set around the call). Rejected: debouncing (visible lag).

**D7. The SVG stays as the fallback**, and as what existing tests exercise. Rejected: deleting it (every existing
`img` test would have to move to a mocked library, and a missing handle would draw nothing).

**D9. The main chart always holds the whole bar sequence.** With `candles` off its candle series gets a whitespace entry for
each bar time instead of `[]`, so its axis is the bars' whatever the layers; index alignment is then a property of the
chart, not of a layer. Rejected: a pane that follows the main chart's layers (the pane would have to know them).

**D10. A new pane chart adopts the main chart's visible range** when it is created (first use, scheme or palette change),
then follows by subscription. Rejected: waiting for the next user move (the pane would sit at its own range until then).

**D11. The pane's container has the main chart's horizontal inset.** The main chart sits in a `Paper` with padding and a
border; the pane gets the same, so equal price-scale widths mean equal plot areas. Measured in a browser (SC-004).

**D8. The legend is a DOM overlay** (title, last value), not the library's series title alone, so it can be named and read
in a test and in a screenshot.

## Tests (written first)

vitest, pure: `alignToBars` (SC-001, SC-002, boundary instant, a forming bar, no bars, one bar), `runsOf`, volume colours
by direction. vitest, with the library replaced (as the chart tests do): `PaneChart` creates a backbone series with every
bar time, the right series type per pane, one line series per run, a zero price line for CVD, `minimumWidth` on both
charts, two-way range sync with exactly one call each way and no echo, crosshair sync, series removed on change, no throw
on unmount after the main chart; `Chart`'s `onReady` hands the API and clears it; `FlowPane` draws the pane chart with a
handle and the SVG without; roles and names unchanged. Python: the screenshots exist, the modules trace.

## Constitution Check

I: a value is shown at a bar that already exists, and none is moved later; no data is requested. VII: display only. XIII:
one slice. XIV: traced. No violations.

## Risks

- Index alignment depends on both charts holding the same time sequence: the backbone and whitespace are what hold it,
  and a test checks the times handed to the library; the screenshot checks the result.
- Two instances double the resize work; `autoSize` is on for both.
- `setCrosshairPosition` needs a price: the pane passes the value at that bar (or zero) and the main passes the close.

## Project Structure

```text
apps/web/src/paneChart.ts        alignToBars, runsOf, volume colours (new, pure)
apps/web/src/PaneChart.tsx       the second chart and its synchronisation (new)
apps/web/src/Chart.tsx           onReady handle
apps/web/src/FlowPane.tsx        PaneChart with a handle, the SVG without
apps/web/src/App.tsx             keeps the handle in state, passes it down
specs/136-lower-pane-chart/screenshots.mjs   live Volume and CVD, light and dark, 1280 and 390
tests/unit/web/test_pane_chart_artifacts.py
```
