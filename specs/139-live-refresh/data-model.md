# Data Model: Live Refresh

## Entities

### RefreshConfig
- `intervalMs: number` — from `VITE_CHART_REFRESH_MS`, default 60_000; `<=0 || isNaN` means disabled

### RefreshState (internal, not persisted)
- `timerId: ReturnType<typeof setTimeout> | null`
- `isLoading: boolean` — true while a load (initial or refresh) is in flight
- `lastRefreshFailed: boolean` — drives the failure notice
- `lastRefreshError: string | null` — detail for the notice

## State Transitions

Initial load: `isLoading=true` → success: `isLoading=false, lastRefreshFailed=false`; failure: `isLoading=false, lastRefreshFailed=true, lastRefreshError=detail`

Refresh tick: if `isLoading` or `pinned` or `hidden` or `disabled` → skip; else `isLoading=true` → same as above.

Visibility change: hidden → clear timer; visible → if live and not loading → run one refresh immediately.