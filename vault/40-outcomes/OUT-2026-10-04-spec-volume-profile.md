---
id: OUT-2026-10-04-spec-volume-profile
step: spec
records: [REQ-WP-089]
commit: null
---

## What was decided

- **Price bins are collected from the trades, from now on.** A bar has the aggressor split for the whole bar and no price inside it; a profile from
  bars is what PRD §14.1 forbids. So there is no history: a 24h profile is complete after a day, and the response and the picture say how much it covers.
- **5-minute blocks of price bins**, not every trade (hundreds of millions of rows) and not minute-by-tick (about fifty million rows a year per symbol).
- **Computed on request from the bins**, as of an instant, rather than stored as snapshots: the same data three times over for a cheap request.
- **A series primitive draws it**, so the bars stay on their price levels as the reader pans, zooms or the price scale autoscales.
- Incomplete blocks (Binance ids) are dropped, not flagged; a profile uses one bin width.

## What is still open

- A backfill from the raw frame archive; HVN/LVN and the other §14.1 outputs; the notional split.
