---
id: OUT-2026-10-13-implement-forming-windows
step: implement
records: [REQ-WP-106]
commit: null
---

## What was done

Specified, planned and implemented [[REQ-WP-106]] (spec 158) in one step.

- `live.ts`: `bucketOpen`, `mergeMinutes`, `aggregate`, `formingBars`.
- `App.tsx`: the live socket is opened on every timeframe of an unpinned view; on a longer timeframe the page requests the one-minute bars from
  the first window with no stored bar (`fetchBars` gained `startNs`), and hands the built windows to the chart and the pane as their live bars.

## Evidence

**RED first**: `liveForming.test.ts` (16) and `appForming.test.tsx` (5) failed before the code. **GREEN**: the web suite (633 tests), `tsc`, and
the pytest artifact file. Two existing test files that counted "bars requests" now ignore the minute request, said in a comment.

**Deployed (2026-10-13, 14:12 UTC)**: the 4h chart of bybit BTCUSDT is free of spinners after 5.7 s, the chip reads live, and the chart's last
candle opens at the current 4h boundary with the live price as its close (the last-price line on the chart is the feed's price, not the
previous window's close).

## What was decided / found

- Built on the page rather than on the server: the minutes are already there and a server-side aggregator would be a second copy of the
  resampler's windows.
- A closed window the table has not got yet is built too, because the table lags by up to twenty minutes after a boundary.
- Nothing is claimed final unless every minute of the window is present and final.

## What is still open

- A week with more than 10,000 minutes since the last stored bar is built from the newest 10,000 (the route's limit).
