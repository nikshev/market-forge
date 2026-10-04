---
id: OUT-2026-10-04-implement-material-ui
step: implement
records: [REQ-WP-083]
commit: null
---

## What was done

All ten tasks. The overview and the chart are a Material UI interface (MUI 9.4.0 on React 18, Emotion) whose
theme is a pure function of the colour scheme and of Telegram's `themeParams`. New modules: `muiTheme.ts`,
`useScheme.ts`, `MarketTypeChip.tsx`, `AppShell.tsx`; the logo is the favicon (`apps/web/public/`).

**RED first.** The five new test files plus two edited ones were written against unchanged source, with MUI
already installed (install order: T002 tests, then T003 `npm i`, so the failures below are about missing
modules, not a missing dependency):

    Error: Failed to resolve import "../AppShell"        from src/__tests__/materialShell.test.tsx
    Error: Failed to resolve import "../MarketTypeChip"  from src/__tests__/marketsCards.test.tsx
    Error: Failed to resolve import "../muiTheme"        from src/__tests__/muiTheme.test.ts
    Error: Failed to resolve import "../useScheme"       from src/__tests__/useScheme.test.tsx
    Failed Tests 5: channelModeChip (2), chartTheme palette (2), marketsFiveRows (1)

**After.** web 340/340 (297 before + the new ones), `make test` 3232 passed, `make lint`, `make typecheck`,
`make web-typecheck` clean, `make web-build` green; `buildHasNoInitData` still passes.

**Bundle gzip:** 104,983 B before (`index-DcuIZKcf.js`, raw 326,537 B) -> 163,597 B after (raw 504.95 kB).
+56 %; Vite warns the chunk is over 500 kB. Recorded, as SC-005 asks; code splitting is not done here.

**Page width at 390 px:** `scrollWidth == innerWidth == 390` on the overview and the chart, in both schemes.
Eight screenshots are in `docs/ui/`, taken by `specs/132-material-ui/screenshots.mjs`.

**What links this requirement to the trace graph.** The vitest tests cannot carry a pytest marker, and Node
stays out of the commit hook (ADR-021), so `make validate` first failed R2 with "found none". The honest fix
is `tests/unit/web/test_material_ui_artifacts.py`, which checks only what needs no Node: the eight screenshots
(names and widths, nothing extra), the dependencies declared and locked, the favicon file, the `@trace`
markers. The behaviour itself (theme, scheme hook, cards, chart colours, roles) is verified by vitest in CI
(`make web-test`); the VERIFIES edge says less than the requirement's whole acceptance.

## Edits to existing tests (the only ones)

- `marketsFiveRows.test.tsx`: it looked for the text "binance · spot"; venue and type are now two chips, so it
  asserts `binance`/`spot`/`perp`/`bybit`/`okx` as separate texts. The roles and names it checks are unchanged.
- `chartTheme.test.ts`: added three cases for `chartLayout(scheme, palette)`; the existing cases are untouched
  and `chartLayout("light")` is still `{}`.

## What looking at the screenshots found

Tests were green and three things were still wrong:

1. **Duplicate chart series.** The chart's data effect created a candlestick and three lines on every run and
   never removed them, so each refetch stacked a new set on the old one -- visible as doubled price-axis
   labels. Present before this requirement (the effect is old); MUI only made it visible. RED
   (`chartSeriesCleanup.test.tsx`, library mocked: "expected 4 to be 1", "expected +0 to be 4"), fixed by
   removing the created series in the effect's cleanup, guarded by `chart.current === instance` so an unmount
   that disposes the chart first does not throw.
2. **Score chips wrapped with an odd indent** inside a `Stack spacing` (the Stack's margin applies to wrapped
   children). Now a flex-wrap box with `gap`.
3. **Stretched link.** A card cannot be one `<a>` without changing the accessible name from the symbol to the
   whole card text, which the existing `Markets.test.tsx` reads. The link is on the symbol and stretched over
   the card with a pseudo-element, so the name stays the symbol and the whole card is clickable.

## What was decided

- The theme is one pure function (`buildTheme(scheme, telegram)`) and the chart takes its colours from it,
  instead of a second hard-coded set; contrast of text on surface is computed in a test, at least 4.5.
- Telegram's scheme wins inside Telegram, `prefers-color-scheme` outside, and both follow a change.
- Back control only on a chart page in a browser; none inside Telegram (it has its own back button).
- Playwright is not a dependency of the project: it is installed outside the repo and the script is committed.

## What is still open

- The notice "this alert did not record which layers were on -- showing the defaults" is misleading when the
  chart is opened without an alert. Separate requirement.
- Candidate extrema are drawn by default and read as noise; panes without data show a dead button; the features
  table has no producer (CVD, OFI could be computed from the trades already stored). Owner asked for these
  after MUI; each is its own requirement.
- The bundle is one 505 kB chunk.
- Not shown on a phone inside Telegram: needs the bot token, tunnel token and a domain (REQ-WP-080).
