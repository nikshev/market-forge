---
id: REQ-WP-103
title: "A page that is waiting says so: every place the page loads shows a spinner, and takes it away when the answer arrives"
type: work-package
prd_ref: "§27, FR-015/FR-016 of REQ-WP-009; owner's report 2026-10-13"
prd_lines: "4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-009, REQ-WP-102, REQ-WP-092]
tags: [web, loading, ux]
hard_gated: false
---

## Requirement

On 2026-10-13 the owner said: "a loading wheel is needed everywhere, because right now it is not clear whether it is a bug or it is
just taking this long to load." The same day the read API was answering a bars request in 54 seconds and the volume profile in 82
(the host's load average was 41): an empty chart, an empty pane and a missing control were what a slow load and a broken page both
looked like.

Every place the page waits shows a spinner with a name, and **takes it away when its own answer arrives, whatever the answer is** --
data, nothing, or a failure, each of which the page already states in words ([[REQ-WP-009]] FR-015/FR-016):

1. **Before the script has loaded**: the page's own HTML shows a spinner (the page was blank).
2. **The overview** (`Markets`): the markets, and the timeframes control.
3. **The chart page**: the timeframes control; the chart (a spinner over it, the chart mounted underneath so it draws the moment bars
   arrive) until the first bars answer; a small mark by the title while a *reload* is in flight; each lower pane until the series it is
   made of has answered (the bars for Volume, the features for the rest) -- with **no claim about the data** while it waits; the volume
   profile; the consensus when its layer is on.
4. **The live feed's chip** says **connecting**, with a spinner, until the feed has spoken -- it is not "delayed" yet, nothing has
   failed -- and then live, or delayed when it is not connected or will not carry this series.

A spinner is a `progressbar`, never a `status`: the page's statements about the data stay the only `status` and `alert` elements.

## Acceptance

- Each spinner above is present while its request is outstanding and absent once it has answered with data, with nothing, and with a
  failure (tests with a request held open).
- No spinner is shown where nothing is waiting (the consensus when its layer is off; a pane that has answered; the chip when live,
  delayed or off).
- A pane that is waiting makes no "no data" claim.
- The page's HTML carries a spinner before the script runs.
- In a browser against the running stack with the data requests held back, the spinners are on screen and are gone when the requests
  complete.

## Trace

<!-- trace:begin -->
<!-- trace:end -->
