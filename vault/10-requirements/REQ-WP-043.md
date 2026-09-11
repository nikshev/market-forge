---
id: REQ-WP-043
title: Bybit linear perpetuals arrive as the same canonical events
type: work-package
prd_ref: "§5.2, §45 Phase 5, §35.6"
prd_lines: "315-319, 6825, 4897-4906"
phase: 5
status: draft
depends_on: [REQ-WP-003]
tags: []
---

## Requirement

PRD §45's Phase 5 lists `Bybit;` as a deliverable and §5.2 says which product:

    ## 5.2. Phase 2 universe

    - Top 20–50 liquid Binance USDⓈ-M perpetuals;
    - Bybit linear perps;
    - OKX swaps.

The PRD also names the documentation to read, in its own reference list:

    - Bybit V5 — Orderbook WebSocket:
      https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook

**The connector's job is to disappear.** [[REQ-WP-003]] established the shape:
normalisation is pure, takes a decoded message and returns a domain model, and
touches no socket — which is what lets §35.6's replay tests say something about
live behaviour. A second venue is worth building only if, past the normaliser,
nothing downstream can tell which venue a bar came from.

**The fixtures are recorded, not written.** [[ADR-004]] decided this for
Binance and the reason generalises: a live message carries fields the
documentation does not mention, and a hand-written sample encodes the author's
misunderstanding as a passing test. Bybit's public streams need no
authentication and no account, so there is nothing standing between this
repository and real traffic.

**Where Bybit differs from Binance is the part that matters.** Binance sends
`m` — whether the *buyer* was the maker — and the aggressor has to be derived.
Bybit sends `S`, which its documentation calls the taker side directly. Two
venues, two conventions, one canonical field; getting that mapping backwards
inverts every order-flow figure built on it and nothing downstream would show a
symptom.

## Acceptance

- A recorded Bybit trade normalises to the same `TradeEvent` a Binance trade
  does, with the aggressor side taken from the venue's taker field rather than
  derived.
- A recorded order-book snapshot and delta normalise to the same models
  [[REQ-WP-003]] produces, and the existing book reconstruction consumes them
  unchanged.
- Event time is the venue's fill timestamp; ingestion time is ours and is never
  market information (PRD §9).
- A sequence gap is detectable from what the venue sends, per its documented
  `seq`/`u` semantics.
- Every fixture is captured from the live public venue by a committed tool, and
  no test opens a socket.
- Nothing about the Binance connector changes.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Scope is **public market data**: trades and the order book. Bybit's funding and
open interest arrive on other channels and belong with the derivatives path,
which already has its readings ([[REQ-WP-026]], [[REQ-WP-031]]) and nothing
writing them. Adding a second venue's private endpoints would need credentials
this project deliberately does not hold.

OKX is the same requirement for a different venue and is deliberately separate:
two connectors landing together would make a failure in either look like a
failure of the idea.
