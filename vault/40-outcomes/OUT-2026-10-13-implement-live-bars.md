---
id: OUT-2026-10-13-implement-live-bars
step: implement
records: [REQ-WP-102]
commit: null
---

## What was done

Implemented [[REQ-WP-102]] (spec 154) as far as the repository goes; status `tested` until the deployed run.

- `bars/builder.py`: `forming()` -- the windows still being built, as bars that say `is_final: false`, read without changing them.
- `live/`: the wire form (the REST bar plus venue and symbol, instants as strings), the ingest's publisher (a forming bar at most
  once a second per series, a final bar always, any broker failure counted and swallowed), the API's cache of thirty minutes per
  series and the relay loop, and the Kafka end (topic created with its retention, a producer that cannot block).
- Ingest: each daemon publishes to Redpanda after taking its trades; the table sink gets a finished bar first and the feed after.
- API: the relay runs with the application and feeds the hub; `/api/v1/live` sends the cache first (an empty snapshot included)
  and then every update; a timeframe other than 1m is acknowledged as not live.
- **Security**: the gate used to close every browser websocket. The live socket takes launch data as a subprotocol and is verified
  like a request; `/ws/market` stays closed. nginx keeps one proxied location, now passing the upgrade.
- Web: `live.ts` (messages, merge, address, back-off), `useLiveBars` (socket lifecycle, coalescing), the main chart's candle series
  updated in place, the panes holding the same bar times, `LiveChip` (live / delayed and why).
- Mutation sweeps: relay 10 (2 equivalent), publisher 9, builder 4, gate 5 (1 equivalent).

## Evidence

**RED first**: the builder, messages, publisher, relay, socket, gate, compose/nginx and web tests failed before the code (import
errors and assertions). **GREEN**: the Python unit suites for those areas, the web suite (590 tests) and `tsc`; the integration
test against the real Redpanda (a bar produced before the consumer existed is relayed and cached; the topic gets 30 minutes' retention).

## What was decided / found along the way

- The gate's rule "a websocket is closed" and the test that the proxy has one location were both load-bearing: putting the socket
  at `/ws/` through a second proxied location would have been an ungated door. Moving it under `/api/v1/` and authenticating by
  subprotocol kept both properties.
- `lightweight-charts` `update()` cannot change a bar older than the last one, so the previous minute's final values could not be
  applied in place; the live effect sets the candle data again instead (cheap at ~500 points) and does not recreate series.
- The chart's data effect re-ran on every parent render in tests because `extrema` had an inline default; it is a constant now.
- A transport signature (`poll`) gained an optional timeout so one relay loop runs over both transports.

## What is still open

- Deployment and the measurement of the last bar's age from a browser.
- Timeframes above 1m are not live (a forming bucket needs the stored 1m bars of the bucket).
