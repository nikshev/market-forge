---
id: REQ-WP-092
title: "The lower pane is a chart on the main chart's own time axis, with a title, a price axis and a shared crosshair"
type: work-package
prd_ref: "§27.3; owner's direction 2026-10-04"
prd_lines: "4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-084, REQ-WP-085, REQ-WP-088, REQ-WP-083]
tags: [web, chart, panes, time-axis, volume, cvd]
hard_gated: false
---

## Requirement

On 2026-10-04 the owner, looking at the Volume and CVD panes, said that it is not clear what the thing under the
chart is, and suggested putting the data on the chart or making a proper chart below with a **matching timeline**.

Read from the code, the owner is right. The lower pane is a small hand-drawn SVG (`FlowPane.tsx`, 720 x 120 px):

- it has **its own time scale** (x is the series' own first-to-last span, drawn in 720 px) and the main chart's is the
  charting library's, so a value does not sit under the candle it belongs to; zooming or panning the chart does not
  move the pane;
- it has **no axis** (no price or value labels), no name for what it shows, no last value and no crosshair, so a
  reader sees a shape and cannot read it;
- it is **narrower than the chart** (720 of about 1,150 px) and, for the Volume pane, positioned by the bar's
  `open_time_ns` while the candles sit at the bar's `close_time_ns`, so it is a bar out of step even where the scales agree;
- its time axis is time-true while the candles' is an index axis, so a hole in the bars is drawn in the pane and hidden
  above it (the same hole in BTCUSDT 15m was visible in both new panes and nowhere on the candles).

This requirement makes the lower pane a **chart of the same library, under the main one, on the main one's time
axis**:

- **Same time axis.** Each value is at the same time as its bar's candle (the bar's close, as the candles use), the pane
  is as wide as the chart and its plot area lines up with the chart's, and zooming or panning either moves both.
- **A crosshair shared** between them, and the time labels of the main chart are the pane's.
- **A title and a last value** inside the pane ("CVD (base)", "Volume") and a value axis with labels; the CVD pane
  has a visible zero line.
- **Volume as bars coloured by the candle's direction** (up/down), **CVD as a line, one series per run**, so a line
  is never joined across a break ([[REQ-WP-088]]) and the alignment with the candles is not disturbed by a break.
- **The other panes** (OFI, funding, ...) draw the same way when they have data.
- **The pane's selector, its roles and names, and the "no data" rules** of [[REQ-WP-084]] are unchanged.
- Optionally, **volume as a histogram at the foot of the main chart** as a layer, the way price charts commonly show it.

It does not change which data a pane has, and it does not decide how a hole in the bars is shown on either chart
([[REQ-WP-086]]); but it must not make the two charts disagree about it: whatever the main chart does with a gap, the pane
does too.

## Acceptance

- For a fixture of bars and a series, the pane's data points carry exactly the times of the candles they belong to
  (a test over the data handed to the library, with the library replaced as the chart tests do); a point with no
  bar is not invented, and a bar with no value is a gap.
- Zooming or panning the main chart changes the pane's visible range to the same, and the reverse; a crosshair move on
  one appears on the other (tests over the subscriptions, with the library replaced).
- The pane is as wide as the chart and its price scale has the same width, so the plot areas line up (measured in a
  browser screenshot at 1280 px and at 390 px).
- The pane shows its title, its last value and a labelled value axis; the CVD pane has a zero line; Volume bars are
  coloured by candle direction; the CVD pane has one series per run.
- The existing pane roles and names ("Pane" group, one button per pane, "no data" disabled buttons, the status messages)
  are unchanged; the existing web tests pass with only the edits each outcome note lists.
- **Looked at:** screenshots of Volume and CVD panes on the live stack, light and dark, desktop and 390 px, are kept
  under `docs/ui/` and each is looked at; what looking showed is recorded.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-136-lower-pane-chart]]
- **Tests:**
    - `tests/unit/web/test_pane_chart_artifacts.py::test_every_module_this_requirement_touches_names_it[App.tsx]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_every_module_this_requirement_touches_names_it[Chart.tsx]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_every_module_this_requirement_touches_names_it[FlowPane.tsx]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_every_module_this_requirement_touches_names_it[PaneChart.tsx]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_every_module_this_requirement_touches_names_it[paneChart.ts]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[cvd-dark-desktop]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[cvd-dark-phone]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[cvd-light-desktop]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[cvd-light-phone]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[volume-dark-desktop]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[volume-dark-phone]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[volume-light-desktop]`
    - `tests/unit/web/test_pane_chart_artifacts.py::test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width[volume-light-phone]`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/FlowPane.tsx`
    - `apps/web/src/PaneChart.tsx`
    - `apps/web/src/__tests__/chartHandle.test.tsx`
    - `apps/web/src/__tests__/flowPaneChart.test.tsx`
    - `apps/web/src/__tests__/paneChartAlign.test.ts`
    - `apps/web/src/__tests__/paneChartLifecycle.test.tsx`
    - `apps/web/src/__tests__/paneChartSync.test.tsx`
    - `apps/web/src/paneChart.ts`
- **Outcomes:** [[OUT-2026-10-04-implement-lower-pane-chart]], [[OUT-2026-10-04-plan-lower-pane-chart]], [[OUT-2026-10-04-spec-lower-pane-chart]], [[OUT-2026-10-04-tasks-lower-pane-chart]]
<!-- trace:end -->

## Notes

The library is `lightweight-charts` 4.2.3, which has no native panes: the likely mechanism is a second chart instance,
two-way synchronised by the visible logical range and the crosshair, with the price-scale widths forced equal. Version 5
has panes built in and would be cleaner, but it changes every call the chart makes (`addCandlestickSeries` becomes
`addSeries`), so an upgrade is a decision of its own, not a side effect of this. The spec verifies the 4.2.3
capabilities it relies on (a settable crosshair position, a minimum price-scale width) before the plan relies on them.
