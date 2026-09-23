# Quickstart: proving the timeframe reaches the chart

Two levels: the suites, which need no stack, and the running deployment, where
the claim "the chart shows candles at the timeframe the link names" is checked.

## Prerequisites

- `make install`
- For the stack section: the dev stack up and `resample` having run at least one
  pass ([[REQ-WP-073]]'s quickstart), so the non-default series exist.

## 1. The suites

```sh
make test-fast                 # pytest: settings, offered(), the route
cd apps/web && npx vitest run  # the control, the query writers, App-level requests
```

Everything backend-side is unit-level and runs in the fast gate. The web suite
is CI's `make web-test` (ADR-021) and is run locally for this feature.

The tests that matter most, by what they would catch:

| test | catches |
|---|---|
| the parameters that reached `fetch` for `tf=4h` and `tf=5m` | the constant `15 * MINUTE_NS` still in place |
| a set the frontend has never seen renders as buttons | a hard-coded timeframe list |
| `tf=7m` → a `role="alert"` naming it, zero fetch calls | a silent fallback |
| click `30m` → `window.location.search` contains `tf=30m`; open it fresh → same first request | a control that changes the screen, not the link |
| toggle the mode → the address carries/omits `as_seen_then` | the mode half of the same defect |
| `?at=…&signal=…&tf=15m` → change timeframe → `at` and `signal` still present | a query writer that drops the rest of the link |
| two clicks, promises resolved in reverse order | a stale response overwriting the last choice |

## 2. The read, against the running stack

`CHANNELFLOW_TIMEFRAMES` must reach the API. In `.env` (created from
`.env.example`) it is `5m,15m,30m,1h,4h,1d,1w`; after `docker compose up -d
--build api`, the read reports the union with the source:

```sh
curl -s localhost:8000/api/v1/timeframes
```

```json
{"timeframes":[
  {"token":"1m","timeframe_ns":60000000000},
  {"token":"5m","timeframe_ns":300000000000},
  {"token":"15m","timeframe_ns":900000000000},
  {"token":"30m","timeframe_ns":1800000000000},
  {"token":"1h","timeframe_ns":3600000000000},
  {"token":"4h","timeframe_ns":14400000000000},
  {"token":"1d","timeframe_ns":86400000000000},
  {"token":"1w","timeframe_ns":604800000000000}
]}
```

The order and the durations are both assertions: ascending by `timeframe_ns`,
and every duration matching a series [[REQ-WP-073]] produced.

## 3. The chart

Open `/chart/binance/BTCUSDT?tf=1h`.

**Before this feature** the heading says `1h` and the page requests
`timeframe_ns=900000000000` regardless — visible in the browser's network panel
as a `bars` request that never carries `3600000000000`.

**After**, the same link:

- the control shows `1m 5m 15m 30m 1h 4h 1d 1w` with `1h` selected;
- the network panel's four requests (`bars`, `channels`, `features/timeseries`,
  `extrema`) each carry `timeframe_ns=3600000000000`;
- the candles are four-hour candles.

Then:

1. Press `5m`. The candles redraw as one-minute five-minute candles and the
   address becomes `?tf=5m`.
2. Press CURRENT REFIT. The address gains `as_seen_then=false`; switch back and
   it is gone.
3. Copy the address, open it in a new tab, and compare the first request with
   the last one the first tab made — they must match (SC-002).
4. Load `/chart/binance/BTCUSDT?tf=7m`. Expect a visible message naming `7m`
   and listing the offered tokens, **no** chart, and **no** `bars` request at
   any substituted timeframe.

## 4. What is still out of reach

- A live push when configuration changes: the set is read once per page load,
  and a deployment restart is required for a `.env` change anyway.
- Styling and component library: deliberately unsettled by
  [[REQ-WP-074]]'s Reference section; whichever is chosen later can replace
  `TimeframeControl`'s markup without reopening the behaviour.
