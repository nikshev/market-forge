---
id: REQ-WP-083
title: "The overview and the chart are a Material UI interface that follows the theme"
type: work-package
prd_ref: "§27, §27.1, §27.3; owner's direction 2026-10-04 (Material UI)"
prd_lines: "4388-4405, 4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-074, REQ-WP-075, REQ-WP-080, REQ-WP-082]
tags: [web, ui, material-ui, theme]
hard_gated: false
---

## Requirement

The pages work and look like a browser's defaults: black serif-less text on white, an unstyled list, grey
buttons. On 2026-10-04 the owner opened the overview, saw five bare lines and asked for "a proper Material UI".
The product is going to be shown, in a browser now and inside Telegram next, so the interface has to look like
one.

This requirement makes the overview (`/`) and the chart (`/chart/<venue>/<symbol>`) a Material UI interface:

- **A theme, not scattered styles.** One theme, built from the colour scheme: Telegram's inside Telegram
  ([[REQ-WP-080]] already reads it), the browser's `prefers-color-scheme` outside. Telegram's own colours
  (background, text, secondary background, button) are used where it supplies them. Light and dark are both
  first-class, and the chart canvas follows the same palette.
- **A shell**: an app bar with the logo and the product's name; a back arrow on a chart page in a browser (in
  Telegram the native back button does that).
- **The overview** as responsive cards, one per market: the symbol (the link), its venue, a market-type chip
  that tells `spot` from `perp` at a glance, and the scores shown as absent where they are.
- **The chart page** with its controls as Material controls: the timeframe selector, the channel-mode switch
  with a chip that makes AS-SEEN-THEN and CURRENT REFIT impossible to confuse (§27.5 calls the difference
  critical), the lower-pane selector, load states as alerts, and the chart in a surface that takes the
  theme's background.
- **Phone width.** A 390 px viewport has no horizontal page scroll; wide control rows scroll within
  themselves.

It changes **how** the pages look and nothing about what they show, ask the API for, or announce to assistive
technology: every role and accessible name the existing tests use stays, and the existing tests pass.

## Acceptance

- The overview and the chart render under one `ThemeProvider` with `CssBaseline`; the theme is a pure function
  of the scheme and of Telegram's theme parameters when present, tested for light, dark and Telegram input.
- With no Telegram, the scheme follows `prefers-color-scheme`; inside Telegram it follows Telegram's.
- The overview lists one card per market in a list named "Markets"; each card is a link whose accessible
  name is the symbol; `spot` and `perp` chips differ in text and in colour; absent scores read "unscored".
- The chart page keeps its heading, its timeframe group (a button per token, `aria-pressed`), its channel-mode
  control (the mode named, the explanation, the switch button), its lower-pane group and its status and alert
  roles — each as the existing tests find them.
- The chart canvas follows the theme in light and dark.
- A browser at 390 px width shows each page with no horizontal page scroll.
- **Looked at:** screenshots of both pages, light and dark, desktop and 390 px, are taken from the running
  build and committed under `docs/ui/`. Passing tests is not the same as looking right, and this is the
  requirement where the difference is the point.
- The production bundle's size before and after is recorded, and it still contains no signed launch string.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-132-material-ui]]
- **Tests:**
    - `tests/unit/web/test_material_ui_artifacts.py::test_every_new_module_names_the_requirement_it_serves[AppShell.tsx]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_every_new_module_names_the_requirement_it_serves[MarketTypeChip.tsx]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_every_new_module_names_the_requirement_it_serves[muiTheme.ts]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_every_new_module_names_the_requirement_it_serves[useScheme.ts]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_no_screenshot_is_left_over_that_the_requirement_does_not_name`
    - `tests/unit/web/test_material_ui_artifacts.py::test_the_logo_is_the_favicon_and_the_file_it_names_is_served`
    - `tests/unit/web/test_material_ui_artifacts.py::test_the_material_dependencies_are_declared_where_npm_ci_reads_them`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[desktop-dark-chart]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[desktop-dark-overview]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[desktop-light-chart]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[desktop-light-overview]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[phone-dark-chart]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[phone-dark-overview]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[phone-light-chart]`
    - `tests/unit/web/test_material_ui_artifacts.py::test_there_is_a_screenshot_of_each_page_in_each_scheme_at_each_width[phone-light-overview]`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/AppShell.tsx`
    - `apps/web/src/ChannelMode.tsx`
    - `apps/web/src/FlowPane.tsx`
    - `apps/web/src/LoadState.tsx`
    - `apps/web/src/MarketTypeChip.tsx`
    - `apps/web/src/Markets.tsx`
    - `apps/web/src/TimeframeControl.tsx`
    - `apps/web/src/__tests__/channelModeChip.test.tsx`
    - `apps/web/src/__tests__/chartSeriesCleanup.test.tsx`
    - `apps/web/src/__tests__/marketsCards.test.tsx`
    - `apps/web/src/__tests__/materialShell.test.tsx`
    - `apps/web/src/__tests__/muiTheme.test.ts`
    - `apps/web/src/__tests__/useScheme.test.tsx`
    - `apps/web/src/main.tsx`
    - `apps/web/src/muiTheme.ts`
    - `apps/web/src/series.ts`
    - `apps/web/src/telegram.ts`
    - `apps/web/src/useScheme.ts`
- **Outcomes:** [[OUT-2026-10-04-implement-material-ui]], [[OUT-2026-10-04-plan-material-ui]], [[OUT-2026-10-04-spec-material-ui]], [[OUT-2026-10-04-tasks-material-ui]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Out of scope: a design system beyond one theme, new pages, the lower panes' content (only their selector), the
chart library's own rendering, and animation.
