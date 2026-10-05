# Implementation Plan: The chart follows the market without a reload

**Branch**: `139-live-refresh` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/139-live-refresh/spec.md`

## Summary

Stage 1 of REQ-WP-090: the page re-runs its existing series load (bars, channel, feature series, extrema, plus volume
profile and DEX depth where they apply) on a configured interval (`VITE_CHART_REFRESH_MS`, default 60 s) and draws the
answers without a reload. The push path (stage 2) is explicitly out of scope per FR-009. Key constraints: no refresh on
pinned charts (`at` present), no refresh on hidden tabs, never two loads in flight, failure keeps the old picture and
states it, and the reader's timeframe/mode/pane/candidates/visible-range are preserved — only the initial load (or a
timeframe/mode change) sets the range.

## Technical Context

**Language/Version**: TypeScript 5.6 (React 18, Vite 5), Vitest 2.1 for unit tests

**Primary Dependencies**: `@mui/material` 9.4 (UI), `lightweight-charts` 4.2.3 (chart), existing `api.ts` fetch layer,
`App.tsx` load orchestration with `loadId` supersede guard

**Storage**: None (read-only refresh; no local persistence)

**Testing**: Vitest with jsdom (unit), existing test harness in `chartTimeframeControl.test.tsx` pattern; Python pytest
for traceability markers (`@pytest.mark.trace("REQ-WP-090")`)

**Target Platform**: Web (desktop and mobile browsers)

**Project Type**: Web application (React SPA in `apps/web`)

**Performance Goals**: Default interval 60 000 ms (configurable via `VITE_CHART_REFRESH_MS`); a tick is skipped when
pinned, hidden, or already in flight; no tight polling even if config is zero/negative/unparseable

**Constraints**: 
- Principle I (no look-ahead): refresh uses only data available at the tick instant (the API already enforces this)
- Principle III (history immutable): refresh adds to drawn data, never rewrites past channels/extrema
- Principle VII (live = replay): the same load function runs on open and on refresh
- Principle X (thresholds configurable): interval is `VITE_CHART_REFRESH_MS`, build-time via Vite
- FR-016 (REQ-WP-009): failed load states failure, never blanks chart or shows as empty market

**Scale/Scope**: One interval timer in `App.tsx`; one in-flight flag; hooks into existing `load()` callback; touches
`Chart.tsx` only to avoid range reset on refresh (already separated in spec)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. No look-ahead | Pass | Refresh reads what API serves at tick instant; API enforces no future data |
| II. Time is not one thing | Pass | No new timestamps introduced; existing `_ns` fields used |
| III. History immutable | Pass | Refresh only adds new bars/channel/extrema; past snapshots untouched |
| IV. Baselines before models | N/A | No ML/GMDH |
| V. Calibration, not accuracy | N/A | No probabilistic scores |
| VI. Every feature documented | Pass | Spec documents interval, behaviour, failure modes |
| VII. Live and replay same code | Pass | Same `load()` runs on mount and on timer |
| VIII. Connectors share one interface | N/A | No new connector |
| IX. No automatic execution | N/A | Signals only |
| X. Thresholds are configuration | Pass | `VITE_CHART_REFRESH_MS` default 60 000 ms |
| XI. Results reproducible | N/A | No research/backtest |
| XII. Correctness precedes performance | Pass | Interval is the requirement's, not optimised |
| XIII. Work incremental | Pass | Stage 1 only; stage 2 separate requirement |
| XIV. Everything traceable | Pass | Spec has `traces: [REQ-WP-090]`; source/tests will carry `# @trace: REQ-WP-090` |

No violations — all gates pass without justification.

## Project Structure

### Documentation (this feature)

```text
specs/139-live-refresh/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts unchanged — same endpoints)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
apps/web/src/
├── App.tsx              # Timer, in-flight guard, loadId integration, visibility listener
├── api.ts               # Unchanged (same endpoints called)
├── Chart.tsx            # No range reset on refresh (existing effect unchanged; load result draws)
├── types.ts             # No new types needed
└── __tests__/
    ├── appRefresh.test.tsx       # Timer, pinned, hidden, in-flight, failure recovery
    ├── chartRangePreserved.test.tsx  # Visible range not reset on refresh
    └── loadStateRefresh.test.tsx   # Failed/empty/ok vocabulary on refresh
```

**Structure Decision**: Single React app in `apps/web`; the timer and visibility logic live in `App.tsx` where the load
orchestration already is; no backend changes (same API endpoints); tests follow existing patterns in `apps/web/src/__tests__/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table omitted.

## Phase 0: Research

No NEEDS CLARIFICATION markers in the spec. All decisions derived from code facts and requirement text. The research phase
records the design decisions made in the spec and confirms no open questions.

**Research Output** → `research.md`:

- **Timer location**: `App.tsx` owns the load orchestration (`loadId`, `load()` callback, `useEffect` deps). The timer
  starts after the first successful offered-set fetch, and restarts on timeframe/mode change (which already supersedes
  via `loadId`). No timer on refused timeframe or failed offered set.

- **In-flight guard**: A module-level `isLoading` ref (or `loadId` extended) prevents a tick from starting while the
  previous load is in flight. The tick is skipped, not queued.

- **Visibility**: `document.hidden` + `visibilitychange` event listener; one refresh on becoming visible.

- **Range preservation**: `Chart.tsx` already sets the range in a `useEffect` on `[bars, channel, signal, profile,
  volumeProfile, overlays, focusAtNs, extrema, showCandidates, mode]`. The fix is to add a `isRefresh` flag (or
  compare data identity) so the effect only sets range on the initial load, not on a refresh that returns equivalent data.
  Simpler: `Chart` receives a `isInitialLoad` prop (true on mount and on timeframe/mode change, false on refresh) and
  only runs the range logic when true.

- **Failure handling**: `App.tsx` already has `setState("failed", detail)` for the initial load. A refresh failure calls
  the same with a prefix "Refresh: " so the `LoadState` component shows it with role `alert`. The previous `bars`,
  `channel`, `extrema`, `pane` state is unchanged, so the chart keeps drawing. On next success, state clears.

- **Config**: `VITE_CHART_REFRESH_MS` in `.env.example`, `vite.config.ts` reads `import.meta.env.VITE_CHART_REFRESH_MS`,
  parsed to number, default 60_000; <=0 or NaN disables timer.

- **Pinned check**: `link.atNs !== null` (already parsed in `parseDeepLink`).

## Phase 1: Design & Contracts

### data-model.md

```markdown
# Data Model: Live Refresh

## Entities

### RefreshConfig
- `intervalMs: number` — from `VITE_CHART_REFRESH_MS`, default 60_000; <=0 or NaN means disabled

### RefreshState (internal, not persisted)
- `timerId: ReturnType<typeof setTimeout> | null`
- `isLoading: boolean` — true while a load (initial or refresh) is in flight
- `lastRefreshFailed: boolean` — drives the failure notice
- `lastRefreshError: string | null` — detail for the notice

## State Transitions

Initial load: `isLoading=true` → success: `isLoading=false, lastRefreshFailed=false`; failure: `isLoading=false, lastRefreshFailed=true, lastRefreshError=detail`

Refresh tick: if `isLoading` or `pinned` or `hidden` or `disabled` → skip; else `isLoading=true` → same as above.

Visibility change: hidden → clear timer; visible → if live and not loading → run one refresh immediately.
```

### contracts/

No new API contracts — the refresh re-uses the exact same endpoints the initial load calls:

- `GET /api/v1/bars`
- `GET /api/v1/channels`
- `GET /api/v1/features/timeseries`
- `GET /api/v1/extrema`
- `GET /api/v1/volume-profile` (when `volume_profile` layer on)
- `GET /api/v1/dex/depth` (when link names a pool)

Query parameters unchanged (`venue`, `symbol`, `timeframe_ns`, `at_ns`, `as_seen_then`, `window`, `chain_id`, `pool`).

### quickstart.md

```markdown
# Quickstart: Live Refresh Validation

## Prerequisites

- Running stack: `make up` (PostgreSQL, MinIO)
- Web dev server: `cd apps/web && npm run dev` (port 5173)
- API serving bars for a live symbol (e.g., `binance:BTCUSDT` 15m)

## Validation Scenarios

### 1. New bar appears without reload
1. Open `http://localhost:5173/chart/binance/BTCUSDT?tf=15m`
2. Wait for initial load (chart renders)
3. Advance test clock by 60s (or wait 60s on live stack with a running ingest)
4. A new finished bar appears on the chart; the visible range is unchanged

### 2. Pinned chart never refreshes
1. Open `http://localhost:5173/chart/binance/BTCUSDT?tf=15m&at=2026-01-01T00:00:00Z`
2. Advance clock by any number of intervals
3. Zero refresh requests issued (network tab)

### 3. Hidden tab pauses, visible resumes once
1. Open live chart
2. Switch to another tab (hide)
3. Advance clock by 2 intervals
4. Zero refresh requests while hidden
5. Return to tab
6. Exactly one refresh runs

### 4. Failure keeps picture, next success recovers
1. Open live chart
2. Mock API to fail `/api/v1/bars` (HTTP 500)
3. Wait for refresh interval
4. Chart still shows old bars; `LoadState` shows "Refresh failed: HTTP 500" (role alert)
5. Mock API to succeed
6. Wait for next interval
7. Notice clears; new bars drawn

### 5. Reader state preserved
1. Open live chart
2. Change timeframe to 1h, mode to CURRENT REFIT, pane to CVD, turn on candidates, pan/zoom chart
2. Wait for refresh interval
3. All five unchanged (timeframe still 1h, mode still CURRENT REFIT, pane still CVD, candidates on, visible range same)

## Expected Outcomes

- All existing tests pass (`make test-fast`, `make web-test`)
- New tests in `apps/web/src/__tests__/` pass
- Traceability: `make graph && make validate` clean
```