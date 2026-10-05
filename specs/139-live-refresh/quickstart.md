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