---
id: REQ-WP-088
title: "CVD and the trade-imbalance features are produced from the trades the ingest already reads, and the CVD pane draws them"
type: work-package
prd_ref: "§15.4, §27.3, §29.5"
prd_lines: "2386-2403, 4423-4436"
phase: null
status: draft
depends_on: [REQ-WP-011, REQ-STORE-002, REQ-WP-027, REQ-WP-084]
tags: [features, cvd, ingest, pipeline, web]
hard_gated: false
---

## Requirement

PRD §15.4 defines trade imbalance and cumulative volume delta:

`delta_t = aggressive_buy_notional - aggressive_sell_notional`

`CVD_t = CVD_{t-1} + delta_t`

with the features: delta per bar; CVD slope; CVD-price divergence; CVD acceleration; normalized delta / total
volume. §27.3 lists CVD as a selectable lower pane.

The code that computes them exists (`features/flow.py`, [[REQ-WP-011]]: `delta_notional`, `cvd`, `cvd_slope`,
`cvd_acceleration`, `normalized_delta`; CVD-price divergence waits on a definition, ADR-013). **Nothing runs it.**
Checked on the live stack on 2026-10-04: every ingest process (Binance, Bybit, OKX) normalises each trade and
hands it to the bar builder only; the trade is not stored and not passed to the feature code, so the features
table has no rows and `/features/snapshot` returns `{}`. The CVD pane therefore reads "no data" ([[REQ-WP-084]]),
which is true.

This requirement connects them: the trades the ingest already reads are turned into the §15.4 features per
bar timeframe, written to the features table, and served by the existing `/features/*` routes, so the CVD pane
draws a line.

- **The same code live and in replay** (Principle VII): one path computes the features from trades, whether the
  trades arrive from a socket or from a captured segment.
- **No look-ahead** (Principle I): a feature at bar time `t` uses only trades with `event_time <= t`.
- **Append-only and idempotent**: re-processing trades already handled writes no second row; a writer reads
  before it writes (ADR-056).
- **CVD is a running sum and needs a stated origin and a stated reaction to missing trades.** A trade the ingest
  did not see (a reconnect, an outage) makes every later CVD wrong by that trade's delta, silently. The
  requirement must say where the sum starts and what is recorded when the stream was interrupted, so a CVD
  from before and after a gap is not presented as one continuous quantity (the same rule as
  [[REQ-WP-087]], one level down).
- **OFI and book features are not here**: §15.3 needs a top-of-book subscription, which the ingest does not have.

## Acceptance

- For a fixture of trades with known aggressive buys and sells, the rows written for a bar equal §15.4's
  formulas: `delta_notional` is buy notional minus sell notional, `cvd` is the running sum, `normalized_delta`
  is delta over the bar's notional (absent, not zero, when nothing traded).
- A feature at bar time `t` is unchanged when trades later than `t` are appended (a test, as for the other
  features: [[REQ-NRT-LEAK]]'s family).
- The same captured trade segment through the live path and through replay produces identical rows.
- Processing the same trades twice writes no duplicate rows.
- A forced interruption of the trade stream is recorded as a discontinuity; the CVD after it is not presented as
  continuous with the CVD before it (withheld or flagged: the spec decides which).
- On the running stack, after deployment, `/api/v1/features/timeseries` for `binance` `BTCUSDT` at 15m returns
  `cvd` for bars on record, and the CVD pane on the chart draws a line from it; a screenshot of the live pane,
  light and dark, is kept under `docs/ui/` and looked at.
- CVD-price divergence is not produced (ADR-013 stands).

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Raised by the owner on 2026-10-04 ("these data should already be there"). What was found: the computation is
done and tested; the wiring is missing. Whether the feature producer lives in the ingest process (which has the
trades) or runs from the frame archive is the spec's decision; the former couples feature production to the
socket process, the latter adds a pass and a lag. Ingest does not persist trades today, so a restart loses the
running sum unless the spec stores or recomputes it.

The same trade intake is what [[REQ-WP-089]] (the volume profile with buy/sell by price level) needs. Aggregating at
the intake into per-bar price bins (buy and sell volume per bin) would feed both this requirement's delta and that
one's profile without storing every trade; the spec for whichever is taken first decides the shape, and the other
must not re-invent it.
