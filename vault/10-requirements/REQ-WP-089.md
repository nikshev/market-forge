---
id: REQ-WP-089
title: "The chart shows a volume profile beside the price axis: volume by price level from trades, split into buy and sell (delta clustering)"
type: work-package
prd_ref: "§14.1, §27.2; owner's direction 2026-10-04"
prd_lines: "2287-2312, 4406-4421"
phase: null
status: draft
depends_on: [REQ-WP-088, REQ-WP-012, REQ-WP-083]
tags: [web, chart, volume-profile, delta, trades]
hard_gated: false
---

## Requirement

On 2026-10-04 the owner said that the whole idea behind "volume" on this chart was never a bar-per-candle
histogram under it. It was **volume aggregated by the price levels the chart shows, drawn at the side of the
chart as delta clustering**: for each price level, how much traded there and how much of it was aggressive buying
and how much aggressive selling.

PRD §14.1 states the measurement: "Compute true trade-based volume by price bins from exchange trades where
available. Do not infer buy/sell direction from candle color if aggressor-side trades are available." Outputs:
POC, VAH, VAL (value area, default 70 %), HVNs, LVNs, profile entropy and skew, distances to POC/VAH/VAL, nearest
HVN/LVN. Profiles: rolling 4h, 24h and 7d. §27.2 lists "volume profile" and "POC/VAH/VAL" among the chart's
toggleable layers.

What exists, read from the code on 2026-10-04:

- `volume/profile.py` ([[REQ-WP-012]]) builds exactly this from `TradeEvent`s: each `Bin` carries `volume`,
  `buy_volume`, `sell_volume` and a trade count; POC, value area (ADR-028), nodes, entropy, skew. Tested.
- The web has an overlay type (`volumeProfile.ts`: bar width relative to the busiest bin, and a role: POC,
  value area, ordinary) and `Chart` takes a `profile` prop, but the type has **no buy/sell split** and the
  page **never passes a profile**: nothing is drawn.
- **No API serves a profile**, and **no trade is stored**: ingest hands each trade to the bar builder and
  nothing else. Without trades there is nothing to bin, which is the same blocker as [[REQ-WP-088]].

This requirement puts the profile on the chart:

- **At the side, on the chart's price levels.** A horizontal bar per price level, drawn beside the price axis,
  vertically aligned with the same prices the candles use, and following the chart as it is zoomed or panned.
- **Delta clustering.** Each level's bar is split into the buy volume and the sell volume traded at it, in two
  colours, so imbalance at a level is visible; the level's delta (buy minus sell) is readable.
- **From trades, with the aggressor side**, never from candle colour (§14.1).
- **POC, VAH and VAL are marked**; the value-area share is the configured 70 % default.
- **A window**: rolling 4h, 24h or 7d, chosen by the reader, 24h by default.
- **No look-ahead** (Principle I): a profile as of `t` uses only trades with `event_time <= t`; in AS-SEEN-THEN
  it is as of the chosen instant.
- It is one of §27.2's layers (`volume_profile`), already part of the link vocabulary and the default layers,
  so it is shown or hidden like the others.

## Acceptance

- For a fixture of trades with known prices and aggressor sides, the profile served for a window has, per price
  bin, `buy_volume` and `sell_volume` equal to the sums of the matching trades; POC is the bin of greatest
  volume; the value area is contiguous, contains the POC and holds at least 70 % of the volume.
- A trade after the profile's instant does not change that profile (a test, as for the other features).
- The chart draws, for a served profile, one bar per bin whose vertical position is the bin's price on the
  chart's own price scale (a test of the mapping from price to position, and a screenshot that shows a bar's
  level agreeing with the axis), split into two colours by buy and sell.
- Hiding the `volume_profile` layer removes the bars; a window choice changes the profile served.
- With no trades in the window there is no profile and the chart says so; it never draws an empty or zero profile.
- On the running stack, after deployment, the BTCUSDT 15m chart shows a profile with its POC and value area; a
  screenshot, light and dark, is kept under `docs/ui/` and looked at.
- Bin width is a configuration value (Principle X) with a stated default, not a constant in the page.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Raised by the owner on 2026-10-04 when the volume pane under the chart ([[REQ-WP-085]], a per-bar histogram that
does follow the letter of PRD §27.3) turned out not to be what was meant. Both stay: §27.3's lower pane is
volume in time; this is volume by price.

Decisions for the spec: where the profile is computed (at ingest into per-bar price bins, which keeps storage
small and is shared with [[REQ-WP-088]]'s intake; or from stored trades on request); how the chart aligns bars to
its price scale (an overlay positioned from the series' own price-to-coordinate mapping is the likely way, since
the library has no native profile); and the default bin width relative to price. A profile built from bars
(spreading a bar's volume across its range) would be an approximation, not §14.1's measurement, and is not
accepted as a substitute.
