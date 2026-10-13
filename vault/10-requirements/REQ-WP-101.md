---
id: REQ-WP-101
title: "A chart is read, not operated: the wheel scrolls the page, and the price axis stays on its auto-fit"
type: work-package
prd_ref: "§27.2, §27.3; owner's report 2026-10-12"
prd_lines: "4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-092, REQ-WP-080]
tags: [web, chart, interaction]
hard_gated: false
---

## Requirement

The owner reported on 2026-10-12 that the chart's X axis "squeezes and stretches" and that the Y scale is wrong. Reproduced in a
browser: with the pointer over the chart the mouse wheel zoomed the time axis and the page did not scroll, the price scale kept
the range of all the data while the candles used a part of the plot's height, and a drag on the price axis, which the library lets
switch its auto-fit off, left a scale nobody chose.

**The first answer was wrong, and the owner said so the next day** ("now it does not scale at all, neither horizontally nor
vertically"): it turned the wheel and the price-axis drag off, which stopped the squeezing by stopping all scaling. The
requirement is what the reader asked for, which is a chart they can scale:

1. The main chart and every pane let a reader **scale**: the wheel zooms the time axis (and only zooms), a drag on the price axis
   scales the price, a double click on either axis puts it back on its auto-fit, pinch works on touch, and the plot can be dragged.
   A vertical touch drag is left to scroll the page.
2. The price scale **follows what is visible**: it is on auto-fit with margins (8 % above and below) that let the candles fill the
   plot, so zooming in on the time axis rescales the price to the candles shown.

## Acceptance

- The options each chart is created with carry the above (tests on what the library is handed; it cannot be drawn in jsdom).
- In a browser against the running stack: a wheel turn over the chart zooms the time axis and the price axis rescales to the visible
  candles; a drag on the price axis scales it; a double click on the axis restores the auto-fit.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-153-reading-interaction]]
- **Tests:**
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_both_charts_are_created_with_the_one_interaction_constant[Chart.tsx]`
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_both_charts_are_created_with_the_one_interaction_constant[PaneChart.tsx]`
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_every_module_this_requirement_touches_names_it[Chart.tsx]`
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_every_module_this_requirement_touches_names_it[PaneChart.tsx]`
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_every_module_this_requirement_touches_names_it[paneChart.ts]`
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_the_behaviour_is_covered_by_a_vitest_file_that_names_the_requirement`
    - `tests/unit/web/test_reading_interaction_artifacts.py::test_the_constant_lets_a_reader_scale_both_axes`
- **Code:**
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/PaneChart.tsx`
    - `apps/web/src/__tests__/readingInteraction.test.tsx`
    - `apps/web/src/paneChart.ts`
- **Outcomes:** [[OUT-2026-10-12-implement-reading-interaction]]
<!-- trace:end -->
