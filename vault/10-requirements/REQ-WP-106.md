---
id: REQ-WP-106
title: "The last candle of every timeframe is live: a 4h chart ends on the window in progress, with the current price as its close"
type: work-package
prd_ref: "§27, §12; owner's direction 2026-10-13"
prd_lines: "4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-102, REQ-WP-073, REQ-WP-092]
tags: [live, chart, timeframes]
hard_gated: false
---

## Requirement

[[REQ-WP-102]] made the 1m chart live and said "1m only; a forming window needs the stored minutes of the window as well as the live
ones". On 2026-10-13 the owner asked for the rest: "the last bar must be real time -- even on 4h it must show the current price".

The table holds **closed windows only** for a longer timeframe: a 4h bar appears after the window has closed and the resampler has run (the
ingest commits fifteen minutes at a time and the resampler every five), so a 4h chart ended on a candle that was up to four hours and
twenty minutes old and the current price was nowhere on it. The window in progress is built on the page from the minutes:

1. The page asks the table for the **one-minute bars from the first window it has no bar for** (the window after the last stored one),
   and keeps the live socket at 1m on every timeframe -- the minutes are the one live feed.
2. `formingBars` builds every window after the last stored bar from those minutes combined with the live ones (a stored minute
   supersedes a live one): first open, highest high, lowest low, last close, summed volume. **The window in progress has the latest
   minute's price as its close.** A window that has closed but is not stored yet is built too -- otherwise the chart would skip a candle for
   up to twenty minutes -- and is **final only if every minute of it is present and itself final**; a window made of what happened to
   arrive is not claimed to be the bar.
3. The chart and the panes get these as their live bars, exactly as on 1m (REQ-WP-102): the candle is updated in place, the panes'
   axis holds the same bars, the volume pane draws a final window's volume and leaves a forming one blank.
4. If the feed is down the window is built from the stored minutes alone (as current as the table), and the chip says delayed.
5. Alignment follows the last stored bar's own window, so a week that opens on a Monday stays on Mondays; with nothing stored, the epoch.

A forming window is never stored, never final and never an input to a feature (REQ-WP-102's rule).

## Acceptance

- `bucketOpen` finds a window from any window's open (including a Monday-aligned week); `mergeMinutes` lets the stored minute supersede;
  `aggregate` is the OHLCV of the minutes and is never final; `formingBars` builds the window in progress with the live price as its close,
  takes the window's high and low over every minute, builds a closed-but-unstored window and calls it final only with every minute present
  and final, builds nothing from no minutes or inside a stored window, and never more than a handful of windows (tests).
- On a longer timeframe the page requests the minutes from the first window it has no bar for, at one minute, with the largest limit; on the
  one-minute chart it requests nothing extra; the chart and the pane receive the same window (tests).
- On the running stack the 4h chart's last candle opens at the current 4h boundary and its close is the live price.

## Trace

<!-- trace:begin -->
<!-- trace:end -->
