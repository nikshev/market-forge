---
id: OUT-2026-10-05-plan-live-refresh
step: plan
records: [REQ-WP-090]
commit: null
---

## What was decided

- **Timer in `App.tsx`**: The load orchestration already lives there (`loadId`, `load()`, `useEffect` deps). The timer
  starts after the offered set arrives, restarts on timeframe/mode change, and is skipped when pinned, hidden, disabled,
  or already loading.
- **In-flight skip**: A boolean `isLoading` ref; the tick reads it and returns early if true. No queue — the requirement
  explicitly forbids piling up requests.
- **Visibility**: `document.hidden` + `visibilitychange`; clear timer on hide, one immediate refresh on show.
- **Range preservation**: `Chart` receives an `isInitialLoad` prop (true on mount and on timeframe/mode change, false on
  refresh). The range-setting effect only runs when true. `App.tsx` passes this because it knows which trigger fired.
- **Failure handling**: Reuses `LoadState`'s `failed` vocabulary (role `alert`). Refresh failure prefixes the detail
  ("Refresh failed: HTTP 500"). Previous data state unchanged so chart keeps drawing. Clears on next success.
- **Config**: `VITE_CHART_REFRESH_MS` in `.env.example`, parsed with default 60_000, `<=0 || NaN` disables. Principle X.
- **No backend changes**: Same endpoints, same parameters. API enforces no look-ahead; worker passes set freshness floor.
- **Stage 2 out**: Recorded as FR-009; interval stays as fallback when push arrives.

## What is still open

- The `isInitialLoad` prop in `Chart.tsx` needs a clean signal from `App.tsx` (mount/timeframe/mode = initial, timer =
  refresh). The spec says only the initial load (or timeframe/mode change) may set the range — this prop is the
  implementation of that rule.
- Live screenshots will be placed in tasks (following bar-gaps and volume-profile pattern).
- Whether to shorten the 5-minute producer passes (requirement says separate; the interval cannot show what the API
  doesn't serve).

## Notes

All constitution gates pass without justification. No NEEDS CLARIFICATION markers remain. The plan records design
decisions already made in the spec; research.md captures the rationale.