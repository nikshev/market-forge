# Implementation Plan: A Material UI interface that follows the theme

**Branch**: `132-material-ui` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

Add Material UI and Emotion; one pure `buildTheme(scheme, telegramParams)`; a `useScheme` hook (Telegram's
scheme inside Telegram, `prefers-color-scheme` outside); an `AppShell`; and rewrite the presentational markup
of the overview and the chart page's controls with Material components **keeping every role and accessible
name**. The chart canvas takes its colours from the theme. Then look at it.

## What planning measured

- **Size of the job**: `App.tsx` 341 lines, `Markets.tsx` 101, `TimeframeControl.tsx` 36, `ChannelMode.tsx` 35,
  `LoadState.tsx` 37, `FlowPane.tsx` 97, `DexBands.tsx` 117, `Explanation.tsx` 68, `PositionView.tsx` 131,
  `Chart.tsx` 190: about 1,150 lines, no stylesheet, inline markup only.
- **The tests' contract** (297 tests): they query by role and name — `heading` (levels 1 and 2), `button`
  (`5m`, `1h`, `OFI (1m)`, `/show current refit/i`, `pressed`), `link` (a symbol), `list` ("Markets",
  "Contribution factors"), `status` (`/Pane/`), `alert`. Material components keep these: `ToggleButton` renders a
  button with `aria-pressed`, `ToggleButtonGroup` a `role="group"`, `Alert` has `role="alert"` and accepts
  `role="status"`, `List` renders a `ul`.
- **Material UI 9.4.0 is installable** and its peer range includes React 18; Emotion 11.14.
- **A browser is available for looking**: Chromium is in the playwright cache and `playwright` installs in a
  scratch directory without touching the repository's dependencies.
- **What the owner saw**: five unstyled lines on white (the overview) and the chart page's default controls.
- **The channel fix already passes a `scheme` into the chart** (`chartLayout`); it gets the theme's colours.

## Decisions, and what each rejected

**D1. One pure theme function.** Rejected: styling components one by one with `sx` colours (no single place to
change a palette); a CSS-variable layer beside MUI (two theming systems).

**D2. Keep every role and name; the existing tests are the contract.** A restyled button must stay the same
button. Rejected: rewriting the tests to the new markup (it would make them pass and stop them guarding
anything). An edit to an existing test is allowed only for markup with no accessible meaning, and is listed.

**D3. A card is a link by `aria-label`.** `CardActionArea` rendered as an `a` with `aria-label={symbol}` keeps
the link's name exactly the symbol while the card shows venue and chips. Rejected: putting the chips inside
the link (the name would become "BTCUSDT binance spot …" and break the tests and the screen-reader reading).

**D4. The scheme is a hook.** Telegram's `colorScheme` inside Telegram (already applied by [[REQ-WP-080]]),
`useMediaQuery('(prefers-color-scheme: dark)')` outside. Rejected: a toggle button (not asked for; the system
and Telegram already say what the user wants).

**D5. The chart takes the theme's colours.** `chartLayout(scheme, palette)` uses the theme's paper, text and
divider for dark; light stays the library default. Rejected: a second hard-coded dark palette that drifts.

**D6. Icons: one.** The back arrow, from `@mui/icons-material`, imported by path. Rejected: the whole package
import; an inline SVG (fine, but then two icon conventions).

**D7. Look at it.** Screenshots in both schemes at two widths, from the running build, are an acceptance item
and are committed; a screenshot script lives with the spec (it needs playwright, which is not a project
dependency). Rejected: judging a UI by its tests — the previous change drew a correct channel and a screenshot
still showed the view was wrong.

## Tests (written first)

vitest: `buildTheme` for light, dark and Telegram input, fallbacks, and a computed contrast ratio; the scheme
hook for both sources; the market-type chip mapping; `AppShell` (one `h1`, the back control by context); the
overview as cards (five, names, chips, "unscored", empty status, pressed timeframe); the channel-mode chip; load
states keep their roles; `chartLayout` with a palette. The existing 297 are the regression guard. In a real
browser (script, recorded): `scrollWidth <= innerWidth` at 390 px on both pages and the eight screenshots.

## Project Structure

```text
apps/web/src/muiTheme.ts  useScheme.ts  AppShell.tsx  MarketTypeChip.tsx   # new
apps/web/src/main.tsx  App.tsx  Markets.tsx  TimeframeControl.tsx  ChannelMode.tsx  LoadState.tsx
  FlowPane.tsx  Chart.tsx  theme.ts                                          # restyled
apps/web/package.json  package-lock.json  index.html  public/logo.svg
apps/web/src/__tests__/muiTheme.test.ts  materialShell.test.tsx  marketsCards.test.tsx
specs/132-material-ui/screenshots.mjs   docs/ui/*.png
```

## Constitution Check

Principle I and the data are untouched. Principle VII (the page is the same code in and out of Telegram) holds:
one theme function, two scheme sources. No violation; Complexity Tracking is empty.
