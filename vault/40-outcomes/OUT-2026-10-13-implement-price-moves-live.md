---
id: OUT-2026-10-13-implement-price-moves-live
step: implement
records: [REQ-WP-108]
commit: null
---

## What was done

Specified, planned and implemented [[REQ-WP-108]] (spec 160) in one step.

## Evidence

**Found by measuring each hop**, not by lowering an interval. A socket probe through the web proxy showed forming bars in one-second bursts:
the Kafka consumer's `consume(500, 1.0)` waited the whole second. Then a topic created before retention was enforced kept seven days and
replayed about 230,000 messages on every API start (38 s of catch-up, all forwarded). **RED first**: the poll-latency test, the two-topic
routing tests and the relay's "replay is not forwarded" test failed against the old code. **GREEN**: unit suites for transport, live and
the websocket; vitest for the range and following; the integration test against a real Redpanda (4 passed, including a topic that
already existed with a seven-day retention); mutation sweeps `live_publisher` (12 caught) and `live_relay` (survivors carry reasons).

**Deployed and measured in a browser**: the socket delivers about 2.5 updates a second per series (1 Hz bursts before); sampled over 24 s the
close moved on most of them (83298 -> 83270) and the price label on the chart moved with it, on 1m and on 4h; the last candle sits clear of
the volume profile.

**Found on the way**: the integration test's fixture built a temporary `AdminClient` and let it be collected before the delete was sent, so
every run left its topics behind (the broker caps partitions); the client is now held until the deletes finish.

## What is still open

- After a deploy the cache is empty for up to ~15 min for the longest windows until finals are replayed (the final topic keeps 30 min).
- The week window is capped at 10,000 minutes (the route's limit).
