---
id: REQ-WP-076
title: The ingest daemon runs for Bybit and OKX, not only Binance
type: work-package
prd_ref: "§5.2, §6.2"
prd_lines: "315-319, 405-420"
phase: null
status: specified
depends_on: [REQ-WP-066]
tags: []
---

## Requirement

§5.2 names the Phase 2 universe, verbatim:

> - Top 20–50 liquid Binance USDⓈ-M perpetuals;
> - Bybit linear perps;
> - OKX swaps.

§6.2's MVP compose list names one ingest service, `ingest-binance` — one per
venue, by its shape. Phase 2 therefore adds services rather than parameters to
the existing one.

### Most of this venue's work is already done, and none of it is wired

The normalisation layer exists for all three and is under test:
`src/channelflow/connectors/bybit/normalize.py`,
`.../okx/normalize.py`, each with its own suite. `VenuePolicy` likewise names
`BINANCE`, `BYBIT` and `OKX` (`src/channelflow/connectors/session.py`).

The live path does not. There is exactly one stream-URL builder,
`binance_stream_url` (`src/channelflow/connectors/websocket.py`); `streams_for`
builds names in Binance's own notation, `f"{symbol.lower()}@aggTrade"`; and
`build_daemon` (`src/channelflow/pipeline/ingest_main.py`) passes `BINANCE` and
the module-level `VENUE` as constants. So the daemon is not venue-agnostic code
waiting for configuration — it is Binance code, and this requirement is what
makes the venue a value.

§46's reference list names the two venues' own documentation — Bybit V5's
orderbook WebSocket and OKX's v5 API — which is where each venue's stream naming
and connection rules come from. They are not assumed to match Binance's.

## Acceptance

- A daemon runs for a venue named in **configuration**, with no venue constant
  left in the wiring path. Proven by starting one for Bybit and one for OKX from
  configuration alone.
- Each venue's stream names are built by that venue's own rule and pinned by a
  test against the names its documentation gives. Binance's `@aggTrade` notation
  is not assumed to generalise.
- Bars from each venue land with that venue's own value in the `venue` column, so
  §29.4's `(venue, symbol, timeframe, open_time)` ordering separates them.
- Raw frames archive under a prefix naming their venue, so one venue's archive
  cannot be read as another's.
- Each venue's connection obeys its own `VenuePolicy` — ping, pong and reconnect
  — rather than Binance's.
- A venue that connects and delivers nothing is **visible**: the condition is
  reported rather than appearing as a symbol that simply has no bars. An
  upper-case stream name on Binance's combined stream already produced exactly
  that silence once, and it was found by measurement rather than by a message.
- One process per symbol per venue, as [[REQ-WP-066]] established, with the same
  refusal when configuration names more.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-121-multi-venue-ingest]]
- **Outcomes:** [[OUT-2026-09-23-spec-multi-venue-ingest]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
