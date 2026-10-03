---
id: REQ-WP-081
title: "The markets the stack ingests are listed, with the market type the venue's stream really is"
type: work-package
prd_ref: "§27.1, §28.1, §6.2"
prd_lines: "4388-4400, 4461-4475, 405-420"
phase: null
status: draft
depends_on: [REQ-WP-021, REQ-WP-075, REQ-WP-076]
tags: [markets, overview, ingest]
hard_gated: false
---

## Requirement

PRD §27.1 makes `/markets` the overview route and §28.1 serves it: one entry per market. The overview
exists ([[REQ-WP-075]]) and the endpoint exists. On 2026-10-03, with five ingest services delivering
bars, `GET /api/v1/markets` answered `{"markets":[]}` — and so the first screen of the product is empty.

The cause is not a bug in either. The list is read from the `markets` table, and **no running process
writes to it**. The code to write one exists (`LakehouseRepository.add_market`, `market_row`) and a
Binance normalizer for the trading rules exists ([[REQ-WP-021]]); nothing calls them in the stack. The
markets table was filled only by tests.

This requirement makes each ingest process register the market it ingests.

### What a registered market is

A row for `(venue, symbol)` with its **market type** and no trading rules. Rules (tick, step, minimum
notional) are not registered: nothing uses them yet ([[REQ-WP-021]] says so), only Binance has a
normalizer, and a network call at start-up to fill a field nobody reads would be a new way for ingest to
fail. A row without rules is a state the table and the API already represent (`instrument` is absent).

### The market type has to be true

The Binance daemon connects to `wss://stream.binance.com:9443`, which is Binance's **spot** stream; the
Bybit daemon to `…/v5/public/linear` and the OKX daemon to a `-SWAP` instrument, which are perpetuals.
PRD §26.1's example alert says "Binance Perp"; this deployment's Binance data is not. Registering all
three as `perp` would be the convenient answer and a false one, shown on the first screen. So the market
type is a property of the **venue registry** — the one place that already holds each venue's URL and
policy — and is not written anywhere else.

### Registering must never cost a bar

Ingest is the product; the overview is not. A failure to register — the catalog unreachable at start,
a commit conflict that does not resolve — is a WARNING that names the venue and symbol, and ingest
continues. The registration is retried the next time the process starts, and not in a loop.

## Acceptance

- **Five rows.** After the stack starts, `GET /api/v1/markets` lists one entry for every `(venue, symbol)`
  an ingest service ingests today — binance BTCUSDT, ETHUSDT, SOLUSDT; bybit BTCUSDT; okx BTC-USDT-SWAP —
  recorded with the date, from the running stack and not from a test.
- **The type is the venue's.** Each entry carries the market type from the registry: binance `spot`,
  bybit and okx `perp`. A test fails if a registry venue has none, or if the Binance stream URL changes
  without the type being reconsidered.
- **Registering twice adds nothing.** Starting the same daemon again leaves one row for its key (a real
  table, read back), however many times it starts.
- **Registering fails softly.** With an unreachable catalog, the daemon logs one WARNING naming the venue
  and the symbol and goes on to ingest (a test through `main`, not through the helper alone).
- **No rules are invented.** A registered market reads back with no instrument, and the API says so
  (nulls), as it does for any market without rules.
- **The overview shows them.** The page's list renders one row per entry, each a link to its chart at the
  chosen timeframe, from the real API response (a test with that response's shape).

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Out of scope: trading rules for Bybit and OKX; scores and ranking (an unscored market sorts after a
scored one and carries nulls, as [[REQ-WP-075]] already says); DEX markets; removing a market that is
no longer ingested.
