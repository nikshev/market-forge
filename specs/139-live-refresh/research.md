# Research: Live Refresh (Stage 1)

## R1. Timer location and the existing load orchestration

`App.tsx` owns the data load: `fetchTimeframes` once, then `load()` callback (guarded by `loadId` ref) that runs
`fetchBars`, `fetchChannel`, `fetchFeatureSeries`, `fetchExtrema`, and optionally `fetchDexDepth` and `fetchVolumeProfile`.
The `loadId` ref supersedes in-flight loads on any dependency change (timeframe, mode, link). A refresh is a third,
fourth, Nth call to the same `load()` through the same guard — the only addition is a timer that fires while the page is
visible and unpinned.

Decision: the timer lives in `App.tsx` (not a separate hook/component) because it needs the same `load()` and `loadId`
and the pinned/hidden checks are pure `link` and `document` state available there. No new component, no prop drilling.

## R2. In-flight skip, not queue

The requirement says "requests do not pile up: a refresh does not start while the previous one is in flight" (Acceptance
5). A boolean `isLoading` ref (set true at `load()` entry, false in its `finally`) is sufficient. The tick callback
reads it; if true, the tick is skipped and the next interval will try again. No queue, no backlog — the requirement
explicitly forbids piling up.

## R3. Visibility and pinned checks

- Pinned: `link.atNs !== null` (already parsed in `parseDeepLink`). The profile fetch and extrema `asOfNs` already
  branch on this; the timer check is the same condition.
- Hidden: `document.hidden` + `visibilitychange` listener. On hide: clear timer. On show: if live (not pinned) and not
  loading, run one refresh immediately, then restart the interval. This matches Acceptance 5 ("refreshes once when it
  becomes visible again").

## R4. Range preservation — the defect inside the defect

`Chart.tsx` has a `useEffect` on `[bars, channel, signal, profile, volumeProfile, overlays, focusAtNs, extrema,
showCandidates, mode]` that calls `instance.timeScale().fitContent()` or `setVisibleLogicalRange()` on every data
change. A timer alone would yank the reader's pan/zoom every minute.

Decision: add an `isInitialLoad` prop to `Chart` (true on mount and on timeframe/mode change, false on refresh). The
range effect only runs when `isInitialLoad` is true. The `Chart` component receives this from `App.tsx`, which knows
whether the load was triggered by a dependency change (initial) or the timer (refresh). Simpler than comparing data
identity, and the requirement's Acceptance 2 explicitly says "the first load sets the range; a refresh does not".

## R5. Failure handling — reuse existing vocabulary

`LoadState.tsx` already defines `empty` (role `status`), `failed` (role `alert`), `disconnected` (role `status`). The
initial load uses `setState("failed", detail)` on a bars error. A refresh failure calls the same with a prefixed detail
so the notice reads "Refresh failed: HTTP 500" — same component, same role, same rule (never blank, never show as empty
market). The previous `bars`, `channel`, `extrema`, `points`, `pane` state is unchanged, so the chart keeps drawing.
`lastRefreshFailed` and `lastRefreshError` track the refresh-specific failure for the notice; they clear on next success.

## R6. Configuration

`VITE_CHART_REFRESH_MS` — Vite build-time env (like `VITE_API_BASE`). `.env.example` documents it. Parsed in `App.tsx`
as `Number(import.meta.env.VITE_CHART_REFRESH_MS) || 60_000`; `<=0 || isNaN` disables the timer. Default 60 000 is the
requirement's own number (Acceptance 1). Principle X satisfied.

## R7. No API or backend changes

The refresh calls the exact same endpoints with the exact same query parameters. The API already enforces no look-ahead
(Principle I), serves point-in-time reads (`at_ns`), and the worker's 5-minute passes set the freshness floor. The page
cannot show what the API does not yet serve — the interval only decides how soon after the API has it the page asks
again.

## R8. Stage 2 (push) explicitly out

The requirement splits stage 2 (worker events → API hub → page WebSocket) and says it may become its own requirement.
This spec records it as out (FR-009). The interval remains the mechanism here; when stage 2 lands, the interval becomes
the fallback (tick fires, but the push already delivered the update — the load returns the same data, no visual change).