---
id: REQ-WP-093
title: "The open-interest, funding and basis panes are fed by a collector that polls each venue's public derivatives data"
type: work-package
prd_ref: "§10.4, §16.1, §16.2, §16.3, §27.3; owner's direction 2026-10-11"
prd_lines: "903-918, 2460-2496, 4423-4436"
phase: null
status: planned
depends_on: [REQ-WP-030, REQ-WP-084, REQ-WP-013]
tags: [derivatives, open-interest, funding, basis, collector, panes]
hard_gated: false
---

## Requirement

On 2026-10-11 the owner looked at the lower-pane row of a chart and saw `Open interest`, `Funding (z)` and
`Basis (bps)` all reading "no data". They asked why, and then asked for every pane to show data.

Read from the code and measured against the running stack: the three features are registered
([[REQ-WP-013]]), the pure functions exist (`derivatives/openinterest.py`, `derivatives/funding.py`) and the
panes exist ([[REQ-WP-030]]), but **nothing produces a `DerivativesState`** (PRD §10.4). The connectors'
`derivatives_state` normalizers have no caller, no table stores their output, and the worker writes only the six
trade-derived features. A pane naming a feature nobody records says "no data" for ever, which is what
[[REQ-WP-084]] made honest and not what the owner wants to see.

This requirement builds the missing producer, end to end, for the venues the deployment already ingests
(Binance, Bybit, OKX):

1. **A collector service** (`context`, one per venue, a compose service on the same image) polls the venue's
   public REST endpoints on a fixed cadence and stores each answer as a `DerivativesState` row in a new
   append-only lakehouse table. It holds no keys. Measured 2026-10-11 from this host: every endpoint below
   answers, and the futures websocket streams the older code comment called unreachable do connect.
   - Binance USD-M futures: `premiumIndex` (mark, index, last funding rate, next funding time),
     `futures/data/openInterestHist` for the open interest **in USD as the venue reports it** (the base-unit
     `openInterest` endpoint is not used for USD: `oi_series` skips base-only states on purpose, because
     multiplying by a price of our choosing would invent a figure the venue did not report).
   - Bybit linear: `tickers` (mark, index, funding, next funding, `openInterestValue` in USD).
   - OKX swap: `open-interest` (`oiUsd`), `funding-rate`, `mark-price`, and the index ticker.
2. **Funding history is loaded once, from each venue's own public history endpoint**, because
   `funding_z` is a 24-settled-interval z-score ([[ADR-026]]: it refuses on fewer) and a venue settles every
   8 hours, so waiting would mean eight days of "no data". A settled rate is public at its settlement time, so
   a history row is a row that existed then: it enters the table with `event_time = settlement time` and is
   tagged as loaded from history, never as polled.
3. **The worker writes the three features per bar, as of the bar's close**, into `feature_snapshots` for every
   (venue, symbol, timeframe) series that has bars, for every timeframe. Rules that hold:
   - **No look-ahead** (Principle I, [[REQ-BIAS-005]]): the value at a bar's close uses only states with
     `event_time <= close`, and only settled funding rates (`settled_funding` is the guard).
   - **Freshness is stated, not inferred**: a state older than the staleness bound is not presented as the value
     now (`require_fresh`). The bound for the polled values is a few poll intervals; for funding the *settlement*
     is allowed to be as old as one interval plus a margin, because a settlement is an 8-hour event and the
     library's 5-minute default would make `funding_z` exist for five minutes in eight hours.
   - **Absence, not zero** ([[REQ-WP-084]]): where a value cannot be computed (collector down, too few settled
     rates, constant series) no row is written, and the pane says so.
   - **A spot series is given its own venue's perpetual**: the Binance series is a spot market and the
     derivatives are the same venue's perpetual of the same pair. This association is stated in the feature's
     source and in the docs, not hidden. `basis_bps` is the perpetual's mark against the venue's index (its spot
     composite).
4. **The deployment runs it**: compose services for the three venues, a health signal, a Prometheus metric for
   the age of the last state, retention through the existing maintenance service, and a section in
   `docs/deployment.md`.

**Not in this requirement**: liquidations ([[REQ-WP-094]]), the order book ([[REQ-WP-095]]), long/short ratios
(§16.5 is "optional when reliable/public"), and cross-venue funding dispersion.

## Acceptance

- A table `derivatives_state` stores `DerivativesState` as §10.4 defines it, append-only, with prices as
  decimals, event time and ingest time kept apart (Principle II), and a column saying whether the row was polled
  or loaded from history.
- For recorded responses of each of the three venues the normalizers produce the expected states, including the
  USD open interest the venue reports; a response missing a field yields a state with that field absent, never a
  default.
- The collector tolerates a failed or rate-limited poll: it records nothing for it, logs it, retries on the next
  cycle, and never writes the previous value again as if it were new. A test with a failing client shows it.
- The history load is idempotent: running it twice stores each settlement once.
- For a stored fixture of states, the writer's `open_interest_usd`, `funding_z` and `basis_bps` at a bar's close
  equal the library functions' values at that instant, are unchanged when states with `event_time` after the
  close are appended (a test), and are absent where the library refuses.
- On the running stack, within one worker cycle after the collector has run for a day, `GET
  /api/v1/features/timeseries` for Binance, Bybit and OKX BTC carries `open_interest_usd`, `funding_z` and
  `basis_bps` at the viewed timeframes, and the three panes are enabled. The check is a recorded query, not a
  claim.
- The existing six trade features are unchanged in value and in count.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-145-derivatives-collector]]
- **Outcomes:** [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

The collector is shared infrastructure for [[REQ-WP-094]] and [[REQ-WP-095]]: one process per venue, one set of
connection, shutdown and health code. [[ADR-070]] records why it is a separate service and why the feature pass
lives in the worker (one writer to `feature_snapshots`).
