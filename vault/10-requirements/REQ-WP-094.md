---
id: REQ-WP-094
title: "The liquidations pane is fed by each venue's public liquidation stream"
type: work-package
prd_ref: "§10.5, §16.4, §27.3; owner's direction 2026-10-11"
prd_lines: "919-931, 2497-2507, 4423-4436"
phase: null
status: planned
depends_on: [REQ-WP-093, REQ-WP-030, REQ-WP-084]
tags: [derivatives, liquidations, collector, panes]
hard_gated: false
---

## Requirement

The `Liquidations (5m)` pane reads "no data" because no source exists: the connectors have **no liquidation
parser at all** (not an unwired one), no `LiquidationEvent` is stored anywhere, and the ingest subscribes to
trades only. The pure window function exists (`derivatives/liquidations.py`: `window`, `intensity`, `clusters`,
`time_since_spike`) and the feature `liquidation_imbalance_5m` is registered.

PRD §10.5 defines the event (`venue`, `symbol`, `event_time_ns`, `side` of `long_liquidated` /
`short_liquidated` / `unknown`, `price`, `qty`, `notional_usd`) and §16.4 asks for long and short liquidation USD
over 1m/5m/15m, the net imbalance, intensity over volume and time since a spike.

This requirement adds, to the collector of [[REQ-WP-093]]:

1. **A liquidation stream per venue**, all public and keyless, probed from this host on 2026-10-11:
   Binance USD-M `<symbol>@forceOrder`, Bybit `allLiquidation.<symbol>` on the linear socket, OKX the
   `liquidation-orders` channel (instrument type SWAP). Each is parsed into the §10.5 event. **The side is the
   side of the position that was closed, which is the opposite of the order's side**: a forced SELL liquidates a
   long. Getting this backwards flips the sign of the feature, so it is pinned by a test per venue from a recorded
   frame.
2. **A table** `liquidations`, append-only, one row per event.
3. **The worker writes the liquidation features per bar**, as of the bar's close, over trailing windows ending at
   the close: `liquidation_long_usd_5m`, `liquidation_short_usd_5m`, `liquidation_imbalance_5m` (the pane),
   `liquidation_intensity_5m` (over the bar's traded USD volume) and `time_since_liquidation_spike`.

Rules that hold:

- **No look-ahead**: only events with `event_time <= close` enter a window.
- **A quiet market is a reading only where the collector was listening.** Zero liquidations in five minutes is
  the true value for a market the collector watched, and a lie for a market it did not. A window is written only
  where the liquidation stream's own connection is known to have been up for every minute of it (the
  stream task stores a heartbeat row per symbol per minute while it is connected; a heartbeat from the REST poller would
  prove the poller was up, not the socket); elsewhere it is absent. And the imbalance of an empty
  window is **absent**, not zero -- `LiquidationWindow.imbalance` already returns `None` there, and the pane
  must not draw "balanced" through a calm hour.
- **Event time is the venue's**; receive time is stored beside it and never decides availability.
- **A venue that sends a side we cannot map is stored as `unknown`**, not guessed.

## Acceptance

- For a recorded frame of each venue the parser yields the expected event, with the position side opposite the
  order side, and `notional_usd = price * qty`.
- A dropped or silent stream is detected (no frame, not even a ping, within a stated window) and reconnects; a
  duplicate frame after a reconnect does not store a duplicate event (identity: venue, symbol, event time,
  price, qty, side).
- For a stored fixture the writer's features at a bar's close equal `window()`'s values, are unchanged when later
  events are appended (a test), and are absent for a window the collector did not cover.
- On the running stack the pane `Liquidations (5m)` is enabled for the series whose venue emitted at least one
  liquidation inside the loaded range, and reads "no data" -- with the reason -- for one that did not. The
  recorded query shows which.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-146-liquidations-collector]]
- **Outcomes:** [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

A liquidation stream is event-driven and sparse for the smaller symbols. A pane that is empty because nothing
liquidated in the range is a correct answer and must be distinguishable from one that is empty because nothing
was listening; the heartbeat rule above is what makes it so.
