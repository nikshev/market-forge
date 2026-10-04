---
id: REQ-WP-082
title: "The chart draws the channel as the model fitted it: a sloped band over its lookback window"
type: work-package
prd_ref: "§13.2, §27.2, §27.5"
prd_lines: "1082-1130, 4406-4421, 4448-4460"
phase: null
status: implemented
depends_on: [REQ-WP-009, REQ-WP-006]
tags: [chart, channels, web]
hard_gated: false
---

## Requirement

PRD §13.2's channel is a regression: a line fitted to the last `lookback` bars of log price, with upper and
lower bounds at residual quantiles. It has a **slope**, and it exists over a **window**. §27.2 lists "channel
center" and "upper/lower" as chart layers.

The chart does not draw that. On 2026-10-04 the owner looked at BTCUSDT 15m and saw no channel. What the page
draws is three **horizontal** lines at the channel's *current* levels (`center_now`, `upper_now`, `lower_now`)
repeated across **every** bar of the history — eight hundred of them, nine days — so a channel fitted to the
last fifteen hours is drawn as a flat stripe across nine days it says nothing about. And the lines are a
quarter of a percent of the price apart (84,763 to 84,974) on an axis stretched to 82,000-89,000 by a spike
four days earlier, and drawn thin and grey, so what is left is a hairline smudge near the last price.

Two causes sit under that, and both are fixed here:

1. **The API does not say what the slope is.** The stored snapshot has `slope_log_per_bar`; `ChannelOut`
   drops it and keeps only `slope_normalized`, the slope in units of the fit's own noise, from which the
   per-bar slope cannot be recovered. The page therefore *cannot* draw a sloped band.
2. **The chart opens on the whole history** (`fitContent`), so a window of sixty bars is a few pixels wide.

The channel must be drawn as the model fitted it, `level(i) = level_now · exp(slope · (i − last))` for the
bars of its window, ending at the bar the snapshot was taken at, so the picture is the same thing the number
describes. The window ends at the snapshot's instant and **not** at the last bar on the chart: in the
as-seen-then view (§27.5) a channel stored at an earlier bar is drawn where it was, not stretched to now.

## Acceptance

- `GET /api/v1/channels` returns `slope_log_per_bar`, equal to the stored snapshot's, and every field it
  returned before is unchanged.
- The channel's three lines are drawn **only over its lookback window**, ending at the last bar closing at or
  before `as_of_ns`, and each is `level_now · exp(slope · (i − last))`: the last point equals the `_now`
  value, and the lines slope the way the model says.
- The upper and lower lines keep their ratio to the centre across the window (they are fixed residual
  offsets in log space).
- A channel stored at an earlier bar ends there, whatever the chart's last bar is.
- A response without a usable slope draws **no** lines: an absent channel is not a flat one.
- With no instant named, the chart opens on the recent bars (two lookbacks) so the channel fills the view;
  the history stays scrollable. With an instant named it opens there, as before.
- The lines are legible: centre solid and thick, upper and lower in the zones' own colours.
- On the live data, BTCUSDT 15m, most closes of the window lie inside the drawn band (the quantiles are 10 %
  and 90 %, so about 80 %): the reconstruction is checked against the data, not assumed.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-131-channel-as-fitted]]
- **Tests:**
    - `tests/unit/api/test_channel_slope.py::test_a_snapshot_stored_before_the_slope_existed_serves_zero_not_an_error`
    - `tests/unit/api/test_channel_slope.py::test_every_field_the_response_carried_before_is_still_there_and_unchanged`
    - `tests/unit/api/test_channel_slope.py::test_the_refit_view_serves_its_own_slope_not_the_stored_one`
    - `tests/unit/api/test_channel_slope.py::test_the_stored_slope_is_served_in_the_as_seen_then_view`
- **Code:**
    - `apps/web/src/__tests__/channelWindow.test.ts`
    - `apps/web/src/series.ts`
    - `apps/web/src/types.ts`
- **Outcomes:** [[OUT-2026-10-04-implement-channel-as-fitted]], [[OUT-2026-10-04-plan-channel-as-fitted]], [[OUT-2026-10-04-spec-channel-as-fitted]], [[OUT-2026-10-04-tasks-channel-as-fitted]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Out of scope: the forecast corridor (§27.2), a filled band (the chart library has no band primitive), and
drawing the channel's *history* — the snapshot stored at each earlier bar — which is the as-seen-then view's
fuller form and needs a range endpoint that does not exist.
