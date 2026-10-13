# Implementation Plan: A live chart

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-102]]

## Design decisions, with what was rejected

1. **The ingest publishes to Redpanda; the API relays.** Reuses [[ADR-063]]'s transport and the existing `/ws/market`. Rejected: the API
   connecting to each venue's websocket itself -- a second set of trade numbers that would disagree with the stored bars at the join;
   an HTTP/WS port on every ingest container -- twelve addresses for the API to know.
2. **Best effort.** The publisher swallows and counts any broker failure; the table is the record and this is a view. Rejected:
   blocking the ingest on the broker.
3. **Forming bars are throttled to one a second per series** and finals are always published, so twelve series are about twelve
   messages a second.
4. **A topic with a short retention** (30 minutes, set when the API or ingest creates it): the API replays it from the start on each
   start with a fresh group, which is the cache. Rejected: a database table for a thirty-minute view.
5. **The page updates the candle in place** (`series.update`) and extends the panes' axis with whitespace points, instead of
   re-running the chart effect on every tick (which recreates every series and overlay).
6. **The socket is `/api/v1/live`, gated by launch data in a subprotocol.** The gate closed every websocket and the public proxy
   reaches `/api//` only; a socket at `/ws/market` would have needed a second proxied location outside the gate. Rejected: launch
   data in the URL (logged), or the live socket open when authentication is required.
7. **1m only.** A forming bucket at a higher timeframe needs the stored 1m bars of the bucket plus the live ones; left to a follow-up.

## Project Structure

New: `live/messages.py` (the wire form), `live/publisher.py` (ingest side), `live/relay.py` (API side: cache + consumer thread), web `live.ts` (merge,
state) and `useLiveBars.ts`. Touched: `bars/builder.py` (`forming`), `pipeline/ingest.py`/`ingest_main.py`, `api/ws.py`, `api/main.py`,
`docker-compose.yml`, `apps/web/nginx.conf`, `Chart.tsx`, `PaneChart.tsx`, `App.tsx`, `.env.example`, `docs/deployment.md`.

## Phases

1. Tests: builder, messages, publisher, relay, hub/ws, web merge/hook/chart/panes. 2. Implementation. 3. Mutations. 4. Gate, commit. 5. Deploy
   (broker config, ingests one at a time, API, web). 6. Measure the last bar's age from a browser.
