---
id: REQ-WP-102
title: "The chart is live: the bars the ingest is still holding reach the browser over a WebSocket, at 1m, without waiting for the table"
type: work-package
prd_ref: "§28.7, §6.3, §27; owner's direction 2026-10-13"
prd_lines: "4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-066, REQ-WP-068, REQ-WP-042, REQ-API-001, REQ-WP-092]
tags: [live, websocket, redpanda, chart, bars]
hard_gated: false
---

## Requirement

The bars table is written fifteen bars at a time ([[REQ-WP-068]]: fewer commits keep the file count and the read cost
down), so a one-minute chart read from the API is up to fifteen minutes behind. On 2026-10-13 the owner decided how to
solve it: **what goes into the bars table is one thing, and the chart gets its own real-time feed**; the live feed is at
**1m**, proxied to the browser over a WebSocket.

1. **The ingest publishes what it holds.** Each ingest daemon publishes its **forming** 1m bar (at most once a second) and
   each **final** 1m bar to the event backbone (Redpanda, [[REQ-WP-042]]) on a versioned topic keyed `venue:symbol`. It is
   best effort: a broker that is down or slow is counted and the ingest carries on, because the bars table is the record
   and this is a view.
2. **The API relays it.** The read API consumes that topic, keeps the last thirty minutes of 1m bars per series, and
   delivers them on a WebSocket at `/api/v1/live` -- the §28.7 socket ([[REQ-API-001]]) under the one prefix the public proxy reaches: on subscribing to `bars` at `1m` the subscriber
   first receives the cached bars (the stretch the table has not caught up on), then every update as it happens. A final bar
   is never replaced by a forming one for the same minute.
   **The socket is gated like everything under `/api/v1/`.** The Telegram gate used to close every browser websocket (a header
   cannot be set on one and a URL is logged); the live socket takes the launch data as a **subprotocol** (`tma`, then the
   data base64url-encoded), is closed (1008) without a valid one, and answers with the scheme only. `/ws/market` stays
   closed to the browser when authentication is required.
3. **The chart uses it.** On the 1m timeframe the page opens the socket, draws the live bars after the last stored one,
   updates the forming candle in place (no redraw of the chart, no change of the reader's zoom), extends the panes' time
   axis so they stay aligned, shows the Volume pane live, says whether it is **live** or **delayed**, reconnects with
   backoff, and falls back to the periodic reload when the socket is down. Panes whose values the worker computes (OFI,
   open interest, ...) are not live and are not drawn as if they were.
4. **A forming bar is not a bar.** It is marked `is_final: false` all the way, is never stored, and no feature reads it
   (Principle I): this feed is for looking, not for computing.

Timeframes above 1m keep the periodic reload in this requirement; their forming bucket is a follow-up.

## Acceptance

- The builder exposes its forming bars without changing them (tests); a bar is the same whether read forming and then
  final or only final.
- A published record carries the bar as the REST bars do (nanosecond instants as strings), `is_final`, the venue and
  symbol, and is keyed `venue:symbol` (tests on a recorded round trip over the in-process transport).
- A broker that raises on publish does not stop the ingest, and the failures are counted (test).
- The relay's cache keeps the newest thirty minutes, replaces a forming bar by a later forming or final one, never a
  final by a forming one, and delivers its snapshot before the first update to a new subscriber (tests).
- A subscriber for another series or timeframe receives nothing (test); a subscription at a timeframe other than 1m is
  acknowledged as not live.
- With authentication required the live socket is closed without launch data, with data that does not verify and with
  signed data under another scheme name, accepts signed data and echoes only `tma`; `/ws/market` stays closed; the public
  proxy still has exactly one location (tests).
- The web: the live bars are merged after the stored ones; a stored bar for a minute supersedes the live one; the candle is
  updated in place; the panes' axis has the same bars; the state is shown; the socket is reopened after it drops (tests).
- On the running stack the last bar of the 1m chart is less than five seconds old, from a browser, with the ingest
  committing fifteen at a time.

## Trace

<!-- trace:begin -->
<!-- trace:end -->
