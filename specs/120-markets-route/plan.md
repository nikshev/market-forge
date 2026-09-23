# Implementation Plan: The markets route

**Branch**: `120-markets-route` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/120-markets-route/spec.md`

## Summary

`App` gains a second branch: `/markets` and `/` render a **Markets** view built
from `GET /api/v1/markets` and the offered set from `GET /api/v1/timeframes`.
Each row is a plain link to §27.1's deep link, carrying the timeframe chosen
with the control the chart already uses. No backend change: every read this
view needs exists ([[REQ-US-001]], [[REQ-WP-074]]).

## Technical Context

**Language/Version**: TypeScript 5 + React 18 (`apps/web/`). Python untouched.

**Primary Dependencies**: React, Vite, vitest + Testing Library — all present.
No new dependency, and specifically no routing library (assumption in the
spec: two routes do not justify one).

**Storage**: none. Reads only.

**Testing**: vitest with `fetch` stubbed, as [[REQ-WP-074]]'s App-level tests
already do. The web gates run in CI (ADR-021) and locally for this feature.

**Target Platform**: the existing static bundle behind nginx. **Verified at
plan time**: `apps/web/nginx.conf:15-16` has `try_files $uri $uri/ /index.html`,
so `/markets` and `/` already reach the bundle — this feature needs no
deployment change, and a routing test pins that the path renders rather than
404s.

**Performance Goals**: none beyond the two reads the view makes; no aggregate
is computed.

**Constraints**: FR-016's vocabulary again. No client-side sort. No new
endpoint.

**Scale/Scope**: one new module (`markets.ts`), one new component (`Markets.tsx`),
one added client function, and `App`'s branch. The default deployment has one
market in the table until scoring runs.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | How this design satisfies it |
|---|---|
| **I. No look-ahead** | The list is a set of current values from a read that already exists; nothing is evaluated at an instant. |
| **II. Time is not one thing** | The view touches no timestamp; the `tf` it carries is a token, and the chart parses it. |
| **III. History is immutable** | Reads only. |
| **IX. No automatic execution** | A list and links; no write path. |
| **X. Thresholds are configuration** | The offered set is read, not written down (FR-005). |
| **XI/XII/XIII** | No dataset, no optimisation, no leap: [[REQ-WP-075]] follows [[REQ-WP-074]], whose command surface it reuses. |
| **XIV. Everything is traceable** | Every source file `// @trace: REQ-WP-075`; tests marked; spec `traces:`. |

No violations. No complexity to track.

## Key decisions

### One component fetches its own two reads; `App` stays a switch

`App` already holds a stable parsed link ([[REQ-WP-074]]). It gains a
mount-stable `path` and a route decision:

```text
path === "/" or "/markets"  -> <Markets />
parseDeepLink(pathname)     -> the chart
otherwise                   -> the existing placeholder
```

`Markets` fetches `markets` and `timeframes` itself and owns the selected
timeframe. Putting the market reads in `App` would make the chart branch carry
state it never uses; a separate component keeps the chart's behaviour exactly
as [[REQ-WP-074]] left it (FR-007).

**The order of the branches matters**: markets first, because `/markets` does
not parse as a deep link and would otherwise fall to the placeholder.

### The destination is built by one pure function

`marketHref(venue, symbol, token)` returns
`/chart/<encoded venue>/<encoded symbol>?tf=<token>`, using
`encodeURIComponent` on the path segments and `URLSearchParams` for the query.
SC-003 wants the destination byte-identical to a pasted link; a function with
its own test is the only way to assert bytes rather than "contains tf".

Why not `URL`/`URLSearchParams` for the whole thing: the app has no origin at
build time, and a relative href is what an `<a>` in this bundle needs.

### Rows are links, not buttons with a handler

An `<a href>` is what a reader can middle-click, copy, or open in a new tab.
Navigation is a full page load, which the chart already handles at mount. The
tests assert `href`, which is the same string the browser uses — a click
handler would need a router to be asserted against.

### `scoreLabel` is a pure function with one job

`scoreLabel(value: number | null): string` returns `"unscored"` for `null` and
a fixed-precision rendering otherwise. Extracting it makes FR-002 testable
without rendering, and keeps the "never render null as 0" rule in one place.

### A failed offered set does not take the market rows down

The rows do not depend on the set; only the timeframe choice does. If the set
fails, the view states it and the row links fall back to `DEFAULT_TIMEFRAME` —
the same default [[REQ-WP-074]] defined once. Hiding the market list because a
control cannot render would make an unrelated failure total.

The reverse case — markets failing — renders the alert and no rows, never an
empty list (FR-006).

### No backend work

§28.1's read exists and is ranked; a second endpoint for the same rows would be
the second-source problem this feature's spec refuses. The one thing checked is
that the API's `markets` route needs no change to serve the web bundle's CORS
or proxy rules: nginx proxies `/api`, and this view uses the same `/api/v1`
prefix as the chart.

## Project Structure

### Documentation (this feature)

```text
specs/120-markets-route/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/web.md     # Phase 1 output
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
apps/web/src/
├── markets.ts                 # NEW: Market type, marketHref, scoreLabel
├── Markets.tsx                # NEW: the view
├── api.ts                     # + fetchMarkets
├── types.ts                   # + MarketOut
├── App.tsx                    # + the route decision
└── __tests__/
    ├── markets.test.ts        # NEW: the pure helpers
    ├── Markets.test.tsx       # NEW: the view
    └── routing.test.tsx       # NEW: which path renders what

docs/deployment.md             # `/` and `/markets` named where the stack is reached
```

**Structure Decision**: the pure helpers live in `markets.ts` and the view in
`Markets.tsx`, the same split `deepLink.ts`/`App.tsx` and
`timeframes.ts`/`TimeframeControl.tsx` already use: everything with a rule is
testable without a renderer.

## Complexity Tracking

No violations to justify.
