# Implementation Plan: The lower panes include volume

**Branch**: `134-volume-pane` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

Frontend only. `panes.ts` gains `BAR_PANES` (volume) beside `PANES`, `ROW` (the two in order), `volumeSeries(bars)`,
and `availablePanes(points, bars)`; `chooseSelection` walks `ROW`. `FlowPane` takes `bars`, renders `ROW`, draws a
bar-sourced pane as vertical bars, and shows the feature failure only for a feature pane. `App` passes the bars.
The comment above the lists is rewritten to be true.

## What planning measured

- `PANES` is parsed by `tests/unit/features/test_pane_features.py` with a regex and each `feature:` is checked
  against the registry. Adding `volume` there would fail it; a separate `BAR_PANES` leaves it unchanged.
- `panes.test.ts` asserts `PANES` has nine entries and their exact order: unchanged by this plan.
- `BarOut` has `open_time_ns`, `close_time_ns`, `volume_base: string`, `is_final`.
- [[REQ-WP-084]]'s own tests (`paneAvailability`, `flowPaneAvailability`, `chartPanesLoading`) count panes
  (nine, "eight no data") and assume the first pane with data is a feature pane. Adding a tenth pane that is
  live whenever bars exist changes those numbers; they are tests of the thing this extends, and the edits are
  listed in the outcome note.
- The live API serves 250-300 bars per series for the three Binance symbols, so the live screenshot has real data.

## Decisions, and what each rejected

**D1. `BAR_PANES` beside `PANES`, joined as `ROW`.** Rejected: an entry in `PANES` with a `source` flag (breaks
the registry check, or forces that test to learn about non-features); a special case for `"volume"` inside
`FlowPane` (the second place that knows the name).

**D2. `volumeSeries(bars)` returns `PaneSeries`**, the same type the feature panes use, so the "empty" / "ok"
messages and availability go through one code path. A bar whose `volume_base` is not a finite number is skipped.
Rejected: drawing it as zero (a claim about the market) or throwing (one bad bar would take the pane away).

**D3. Time = the bar's `open_time_ns`.** Rejected: `close_time_ns` (the chart's candle time; either is a
defensible instant, but a pane has its own scale and "when the bar began" is the plainer reading of a per-bar
amount).

**D4. Volume's availability does not wait for the features, and has its own "loaded" fact.** `App` gets
`barsLoaded` (true when `fetchBars` answered ok, including with no bars; `state` cannot say it, because it
starts at `"ok"` before any load). `FlowPane` takes `barsLoaded` and disables Volume as "no data" iff
`barsLoaded` and `volumeSeries(bars).state !== "ok"`, whatever `available` is. For the feature panes `available`
keeps REQ-WP-084's meaning (`null` until the series answers). The selection rule is unchanged: `available`
(which includes `volume` once bars are final) feeds `chooseSelection`; while it is `null` the choice is left
alone, and the page starts on Volume. A failed feature load shows its message only when a feature pane is
selected. Rejected: waiting for the features before offering Volume (it would hide the one pane that has data
behind a request that can fail); inferring "loaded" from `state` or `bars.length` (both are the same before a
load and after an empty one).

**D5. Vertical bars, not a line.** Volume is an amount per bar. Rejected: reusing the polyline (a line through
volumes reads as a trend).

**D6. The comment is corrected, not deleted.** It names the nine §27.3 panes, which have data (volume), which
have none yet, and the extra `depth_imbalance_10`.

## Tests (written first)

vitest: `volumeSeries` (twelve final bars + one non-final → twelve values equal to `volume_base`; a zero is
drawn at zero; a precise decimal survives; a non-numeric value is skipped, not zero; no final bars → empty);
`availablePanes(points, bars)` (Volume present iff a final bar exists; features unchanged); `chooseSelection`
over `ROW` (Volume first when it has data); `FlowPane` (Volume first; draws one rect per final bar; a feature
failure does not hide it; disabled "no data" with no bars); `App` (opens on Volume with bars and an empty
series; Volume stays live when the feature load fails). Python: the live screenshots exist, the module traces.

## Constitution Check

I: nothing here reads later than the bars already loaded; a non-final bar is excluded, which is the same rule
the chart applies. VII: display only. XIII: one small slice. XIV: traced. No violations.

## Project Structure

```text
apps/web/src/panes.ts        BAR_PANES, ROW, volumeSeries, availablePanes(points, bars), chooseSelection
apps/web/src/FlowPane.tsx    bars prop, ROW, bar drawing, failure only for feature panes
apps/web/src/App.tsx         passes bars; first pane is Volume
specs/134-volume-pane/screenshots.mjs                 live Volume pane, light and dark
tests/unit/web/test_volume_pane_artifacts.py          screenshots exist, modules trace
```
