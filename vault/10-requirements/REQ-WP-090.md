---
id: REQ-WP-090
title: "The chart page follows the market: new bars, the channel and the extrema appear without a reload"
type: work-package
prd_ref: "§27, §28.7; owner's direction 2026-10-04"
prd_lines: "4382-4462, 4526-4540"
phase: null
status: planned
depends_on: [REQ-WP-009, REQ-API-001, REQ-WP-083]
tags: [web, chart, live, polling]
hard_gated: false
---

## Requirement

On 2026-10-04 the owner looked at an ETHUSDT chart and noted that it does not update online. Read from the code:

- the page loads its data **once** (on open, and when the timeframe or the channel mode changes); there is no
  polling and no WebSocket client in `apps/web`, so a new candle appears only after a manual reload;
- the API has a WebSocket (`/ws/market`, PRD §28.7, [[REQ-API-001]]) with a subscription on `bars`, `channel`,
  `features` and `signals`, tested in isolation; but nothing in the API or the pipeline calls the hub's `publish`
  in the deployed split (the replay's event bus lives in the worker process, the hub in the API process), so no
  event reaches it. Not verified end to end;
- the data itself is only as fresh as its producers: higher timeframes are built by `resample` every 5 minutes
  (`CHANNELFLOW_RESAMPLE_INTERVAL`) and channels and extrema by the worker every 5 minutes
  (`CHANNELFLOW_CHANNEL_INTERVAL`), so a finished 15m candle and its channel appear at the API minutes late.

This requirement makes the page follow the market in two stages, the first of which does not wait for the second:

1. **Refresh by reading again.** While the page is visible, it re-reads the bars, the channel and the extrema (and
   the feature series) on a configured interval, and updates what is drawn, **keeping the reader's state**: the
   selected timeframe and mode, the pane, the candidate switch, the visible range the reader chose.
2. **Push.** The API's WebSocket is wired to the worker's events so that a finished bar and its channel reach the
   page as they are produced, and the page subscribes. The reading interval then becomes a fallback.

Rules that hold in both: a chart pinned to an instant (a deep link with `at`, which is a historical view) does not
move; a failed refresh keeps the old picture and says so, and never blanks the chart or shows a failure as an empty
market; a hidden tab does not poll; and nothing here may make a past channel snapshot or a confirmed extremum
change, only add to what is on record (Principle III).

## Acceptance

- With the page open on a live (unpinned) chart, a bar finalised after load appears on the chart within the
  configured refresh interval (default 60 s) without a reload, shown by a test with a clock and a replaced API,
  and on the running stack.
- A refresh keeps the selected timeframe, channel mode, lower pane, candidate switch and the visible range the
  reader set; a test changes each, refreshes, and finds them unchanged.
- A chart opened with `at` (a historical view) issues no refresh requests.
- A refresh that fails leaves the previous data drawn, states the failure, and the next refresh recovers it.
- A hidden tab (`visibilitychange`) issues no requests and refreshes once when it becomes visible again.
- Requests do not pile up: a refresh does not start while the previous one is in flight.
- The interval is a configuration value (Principle X).
- Stage 2 (the push path), when taken: an event published in the worker for a finished bar reaches a connected
  client through the API's hub, shown by an end-to-end test across the two processes, and the page applies it
  without a second read.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-139-live-refresh]]
- **Outcomes:** [[OUT-2026-10-05-spec-live-refresh]]
<!-- trace:end -->

## Notes

Stage 1 is small and independent. Stage 2 crosses a process boundary (worker to API) and is a design decision of
its own; it may be split into its own requirement when specified. The latency floor is set by the producers'
5-minute passes, not by the page, and whether to shorten them is separate.
