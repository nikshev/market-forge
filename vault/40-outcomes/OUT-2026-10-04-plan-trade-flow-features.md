---
id: OUT-2026-10-04-plan-trade-flow-features
step: plan
records: [REQ-WP-088]
commit: null
---

## What was decided

- **A pure `flow_rows(bars)`** in `features/flow_bars.py`, run by the worker pass that already reads every series'
  bars, written through a sink that reads the latest row on record first (ADR-056). Six features registered.
- **The CVD pane entry becomes `cvd_base`, label "CVD (base)"**; the line breaks at a `cvd_run` change.
- **A `sequential_trade_ids` flag on the venue registry**, true for Binance only (measured).

## What was rejected

- A trade-level producer in the ingest (new coupling to the socket process, a second source of 15m flow beside the
  bars, and it redoes what the bar builder already did).
- Adding the quote split to the bar now (a schema change to the central table, forward-only, no history);
  notional as base times VWAP (invents a number); writing base-unit values under the name `cvd` (the registered
  feature would claim a unit it does not have).
- The API computing on read (the served series would differ from the stored one).

## What is still open

- One existing test line changes: `panes.test.ts` expects the pane list with `cvd`; it becomes `cvd_base`.
