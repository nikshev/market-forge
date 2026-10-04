---
id: REQ-WP-086
title: "A missing bar is visibly missing: the chart marks a gap in the bar series and says how much is absent"
type: work-package
prd_ref: "§32 Data Quality Layer; owner's direction 2026-10-04"
prd_lines: "4752-4782"
phase: null
status: draft
depends_on: [REQ-WP-083, REQ-WP-009]
tags: [web, chart, data-quality, bars]
hard_gated: false
---

## Requirement

On 2026-10-04 the owner pointed at an ETHUSDT 1h chart and asked how an extremum there had been confirmed. The
picture looked like consecutive hours; it was not. Measured the same day against the running API (hourly bars,
the latest 500 requested):

| series | bars returned | hourly bars missing between them |
|---|---|---|
| ETHUSDT | 254 | 153, of which one hole of **148** (26.09 06:00 → 02.10 11:00) and three of 1-2 |
| BTCUSDT | 301 | 109 |
| SOLUSDT | 253 | 154 |

The chart plots bars one after another on an index axis, so a hole of 148 hours is drawn as no hole at all: two
candles that are a week apart sit side by side, with the channel, the extrema and the pane drawn across them. A
reader cannot tell the picture is discontinuous, and "confirmed 10 bars later" (the API's
`confirmation_lag_bars`) can mean ten hours or ten days.

PRD §32 makes data quality a layer of its own: health metrics include **missing bars**, and a series has a
quality state (`GOOD`, `DEGRADED`, `STALE`). This requirement makes the *presentation* honest about it:

- **A gap is visible.** Wherever consecutive bars of a series are more than one timeframe apart, the chart
  shows a discontinuity at that place, and says how many bars are absent and over what span (for example "148
  hourly bars missing, 26.09 06:00 to 02.10 11:00").
- **Nothing is drawn across it as if continuous.** The candles on either side are not joined by anything the
  chart draws as one continuous object across the hole without saying so.
- **The count is derived from what the page already has**: each bar carries its open and close times and the
  timeframe is known, so a missing bar is a bar that the spacing says should exist and does not. No new API
  field is required; a server-side quality field is not ruled out but is not assumed.
- **An absent bar is not a quiet bar.** A bar that exists with volume `0` is data; a bar that does not exist is
  absence, and the two never look alike.

It does **not** decide what the detector or the channel do across a gap ([[REQ-WP-087]]), and it does not
backfill anything.

## Acceptance

- Given bars with a hole of N missing bars between two present ones, the chart shows one discontinuity marker
  at that place stating N and the span; given contiguous bars, no marker.
- The marker count equals the number of timeframe steps absent, computed on a fixture (a hole of exactly one
  bar, of several, and two holes in one series).
- A bar present with volume `0` shows no marker.
- On the running stack, the ETHUSDT 1h chart shows the 148-bar hole as a hole; a screenshot, light and dark, is
  kept under `docs/ui/` and looked at.
- The roles and names the existing tests find are unchanged; the marker is not announced as a data point.
- A chart with no gaps looks as it does today.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Found by the owner's question about a confirmed extremum on ETHUSDT 1h; the ETH and SOL ingest containers had
been running for 11-18 hours when this was measured, so part of what is missing is history that was never
ingested for those symbols and part may be outages. Telling those apart is [[REQ-WP-087]]'s side of the work and
not this note's. The mechanism (whitespace points on the chart's time axis versus a drawn marker) is the
spec's to settle; whitespace would give the hole its true width and would change the chart's visible range
logic, which is why it is not decided here.
