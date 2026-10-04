---
description: "Tasks for REQ-WP-083 — a Material UI interface that follows the theme"
---

# Tasks: A Material UI interface that follows the theme

**Tests** first, run RED; the existing 297 web tests are the regression guard and are **not edited** except for markup with no accessible meaning, each listed in the outcome note.

- [ ] T001 Record the **before**: screenshots of both pages (light, desktop) from the running build; the gzip size of the bundle; the number of web tests (297)
- [ ] T002 Write the failing tests (vitest): `muiTheme.test.ts` (light, dark, Telegram parameters, fallbacks, computed contrast of at least 4.5), the scheme hook (Telegram's inside Telegram, `prefers-color-scheme` outside, and following a change), `materialShell.test.tsx` (a single `h1`, the back control only on a chart page in a browser, none in Telegram), `marketsCards.test.tsx` (five cards in a list named "Markets", links named by symbol, `spot`/`perp` chips that differ in text and colour, "unscored", the empty status, the pressed timeframe), the channel-mode chip, `LoadState` roles, `chartLayout` with a palette. RED, recorded
- [ ] T003 `npm i @mui/material @emotion/react @emotion/styled @mui/icons-material` in `apps/web` (lockfile committed; `npm ci` is what CI runs)
- [ ] T004 Write `muiTheme.ts`, `useScheme.ts`, `MarketTypeChip.tsx`, `AppShell.tsx`; copy `assets/logo.svg` to `apps/web/public/logo.svg` and use it as the favicon; wrap the app in `ThemeProvider` and `CssBaseline` in `main.tsx`. `// @trace: REQ-WP-083` in each
- [ ] T005 Restyle `Markets.tsx` (cards in a responsive grid, timeframe `ToggleButtonGroup`), `TimeframeControl.tsx`, `ChannelMode.tsx` (mode chip), `LoadState.tsx` (`Alert`), `FlowPane.tsx` (`ToggleButtonGroup`), and the chart page's layout in `App.tsx`, keeping every role and name; make `Chart.tsx`/`theme.ts` take the theme's colours
- [ ] T006 Run the new tests and **all** existing web tests: the existing ones pass unchanged; list any edit with its reason
- [ ] T007 Rebuild and recreate `web` only. With the scratch playwright script (`specs/132-material-ui/screenshots.mjs`): the eight screenshots (overview and chart, light and dark, 1280 px and 390 px) into `docs/ui/`; **look at each**; measure `scrollWidth <= innerWidth` at 390 px on both pages. Fix what the looking shows, and record each thing it showed
- [ ] T008 Record the bundle's gzip size after, and that a production build still contains no signed launch (`buildHasNoInitData` passes)
- [ ] T009 `make lint typecheck test web-typecheck web-test web-build`
- [ ] T010 Write the implement outcome note; set `implemented`; `make graph && make validate`; commit

## Coverage

| requirement | task |
|---|---|
| FR-001 one provider and baseline | T002, T004 |
| FR-002 pure theme | T002, T004 |
| FR-003 scheme sources | T002, T004 |
| FR-004 cards, links, type chips | T002, T005 |
| FR-005 roles and names unchanged | T006 |
| FR-006 mode chip | T002, T005 |
| FR-007 chart follows the theme | T002, T005 |
| FR-008 no horizontal scroll at 390 px | T007 |
| FR-009 screenshots committed | T007 |
| FR-010 no launch string in the bundle | T008 |
| SC-001 existing tests pass | T006 |
| SC-002 contrast | T002 |
| SC-003 `scrollWidth` | T007 |
| SC-004 eight screenshots looked at | T007 |
| SC-005 bundle size | T001, T008 |

## Dependencies

T001 first; T002 → T003 → T004 → T005 → T006; T007 after T006; T008 and T009 after T007; T010 last.
