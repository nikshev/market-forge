---
id: REQ-WP-088
title: "CVD and the trade-imbalance features are produced from the aggressor volumes the bars already carry, and the CVD pane draws them"
type: work-package
prd_ref: "§15.4, §27.3, §29.5"
prd_lines: "2386-2403, 4423-4436"
phase: null
status: planned
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

The code that computes them exists (`features/flow.py`, [[REQ-WP-011]]), over trades, in notional. **Nothing runs it.**
Checked on 2026-10-04: the features table has no rows and `/features/snapshot` returns `{}`, so the CVD pane reads
"no data" ([[REQ-WP-084]]), which is true.

**The data is already stored, in another form.** Every bar in the lakehouse carries the split by aggressor side:
`aggressive_buy_base`, `aggressive_sell_base`, `delta_base`, `trade_count`, `first_trade_id`, `last_trade_id`
(`resample` sums them for every timeframe, from complete windows). The API does not expose them. They are in **base
units**; PRD §15.4 says notional, and the bar stores only the quote total, so this requirement produces the
features **in base units, under `*_base` names**, recorded as a knowing deviation in [[ADR-068]] with the way back.

This requirement derives the §15.4 features from those stored bars, per timeframe, in the worker pass that already
reads them, writes them to the features table, and serves them through the existing `/features/*` routes, so the CVD
pane draws a line.

- **One pure function for every pass and replay** (Principle VII): the features are a function of the bars.
- **No look-ahead** (Principle I): a feature at bar time `t` uses only bars at or before `t`; a forming bar produces none.
- **Append-only and idempotent**: a second pass over the same bars writes no second row; a writer reads before it
  writes (ADR-056).
- **CVD is a running sum, so a break must end it.** A missing bar, or (where the venue's trade ids are sequential:
  Binance, measured; Bybit and OKX are not) a missed trade, makes every later value wrong by an unknown amount. The
  sum is kept within a **run** of consecutive bars; a break starts the next at zero; the chart breaks the line at it.
- **OFI and book features are not here**: §15.3 needs a top-of-book subscription, which the ingest does not have.

## Acceptance

- For a fixture of bars with known aggressor volumes, the rows written for a bar are: `delta_base` buy minus sell,
  `cvd_base` the running sum within the run, `normalized_delta_base` the delta over `volume_base` (absent, not zero,
  when nothing traded), `cvd_base_slope`, and `cvd_base_acceleration` (absent in a run's first bar). No row is
  named `cvd` or `delta_notional`.
- A feature at bar time `t` is unchanged when bars later than `t` are appended (a test, as for the other features:
  [[REQ-NRT-LEAK]]'s family); a forming bar produces none.
- A missing bar ends the run: removing the middle of three bars gives two runs and no sum across the gap. For
  Binance a trade-id jump between bars ends it too, and a bar whose id span differs from its `trade_count` produces
  no row; Bybit and OKX break on a missing bar only (measured limit).
- A second worker pass over the same bars writes no duplicate row, for every timeframe the worker processes.
- The same bars give the same rows in any order and in any pass (one pure function).
- On the running stack, after deployment, `/api/v1/features/timeseries` for `binance` `BTCUSDT` at 15m returns
  `cvd_base`, and the "CVD (base)" pane draws a line from it, broken where the run changes; a screenshot of the
  live pane, light and dark, is kept under `docs/ui/` and looked at.
- The deviation from PRD §15.4 (base units, not notional) is recorded in [[ADR-068]] with the way back.
- CVD-price divergence is not produced (ADR-013 stands).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-135-trade-flow-features]]
- **Outcomes:** [[OUT-2026-10-04-plan-trade-flow-features]], [[OUT-2026-10-04-spec-trade-flow-features]], [[OUT-2026-10-04-tasks-trade-flow-features]]
<!-- trace:end -->

## Notes

Raised by the owner on 2026-10-04 ("these data should already be there"). The first reading was that the trades were
not stored and a trade-level producer was needed. Reading the bars table showed they are not needed: the aggressor
split, the trade count and the first and last trade id are stored per bar, at every timeframe, and have been since
each series' ingest started. The unit is base, not notional, which is the whole of the deviation ([[ADR-068]]).

[[REQ-WP-089]] (the volume profile with buy and sell by price level) is different: it needs trades by price, and a
bar does not carry them. It will need a trade intake of its own, which this requirement no longer provides.
