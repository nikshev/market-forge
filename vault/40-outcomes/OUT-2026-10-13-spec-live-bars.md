---
id: OUT-2026-10-13-spec-live-bars
step: spec
records: [REQ-WP-102]
commit: null
---

## What was done

Specified and planned [[REQ-WP-102]] (spec 154) in one step: the owner decided that the bars table and the chart's feed are separate things, and
that the chart's real-time feed is a WebSocket at 1m.

## What was decided

- **Ingest -> Redpanda -> API -> `/ws/market` -> browser**, on the transport and the socket that already exist and were never connected.
- **Best effort**, throttled to one forming bar a second per series, thirty-minute retention, in-place candle updates, panes extended with whitespace.
- **1m only**; the forming bucket of a higher timeframe is a follow-up.

## What is still open

- Whether the 15-bar commit batch should shrink now that the chart does not depend on it (not changed here).
