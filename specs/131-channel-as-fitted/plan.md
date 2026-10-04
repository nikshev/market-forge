# Implementation Plan: The chart draws the channel as the model fitted it

**Branch**: `131-channel-as-fitted` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

Expose `slope_log_per_bar` in `ChannelOut`; rewrite `buildSeries`' channel lines to be the sloped lines over
the lookback window ending at `as_of`; open the chart on the recent bars when no instant is named; make the
lines legible. Three small changes in two layers, each with a test that fails first.

## What planning measured

- **Cause found by reading** `apps/web/src/series.ts`: `at(value)` maps *every* candle to one value, so the
  three lines are flat over the whole history. Live the channel is 0.249 % wide (84,763-84,974) on a 800-bar
  view whose axis spans 82,000-89,000.
- **The slope is stored and dropped**: `tables/channels.py` has the `slope_log_per_bar` column and
  `ChannelSnapshot` the field; `ChannelOut.of` does not copy it. `slope_normalized` (slope over residual std)
  cannot be inverted to the per-bar slope without the std, which the snapshot does not expose.
- **The model's indexing**: `index = np.arange(len(window))`, bars not time; bounds are `exp(fitted[-1] +
  low_q|high_q)`, so the lines are exactly `level_now · exp(slope · (i − last))`.
- **An existing test encodes the old behaviour** (`Chart.test.tsx`: one point per bar, all equal). It asserts
  the fault; it changes with this requirement and the change is recorded.
- **Live data**: the API at `at_ns=now` returns `lookback 60`, `slope_normalized 0.0043`; the reconstruction
  is checked against the window's closes (SC-002).

## Decisions, and what each rejected

**D1. Reconstruct in the page from `level_now` and the slope.** Rejected: an endpoint returning the line
points (the page would draw what the server computed, and the formula is three lines); drawing the stored
snapshot at every earlier bar (the fuller as-seen-then picture, needs a range endpoint — out of scope).

**D2. Window ends at `as_of`, by bar close.** The last candle with `close_time_ns <= as_of_ns`; not the
last candle of the chart.

**D3. No usable slope draws nothing.** A flat line would be a boundary no model produced.

**D4. The default view is three lookbacks.** Rejected: fitting the whole history (the cause); a fixed bar
count (the channel's own size is the right scale).

**D5. Colours from the zones.** Upper red, lower green, centre blue; centre solid at width 3, the others
dashed at width 2.

## Tests (written first)

pytest: `ChannelOut` carries the stored slope in both modes and every earlier field is unchanged; the route
returns it. vitest: the lines' length, end and values for a known slope; the ratio constant; an earlier
`as_of`; fewer bars than the lookback; a non-finite slope; `visibleRangeForChannel`; the legibility
constants; and the old whole-history test replaced by these.

## Project Structure

```text
src/channelflow/api/schemas.py                  # slope_log_per_bar on ChannelOut
apps/web/src/types.ts  series.ts  Chart.tsx     # the type, the series, the view and the style
tests/unit/api/test_channel_slope.py            apps/web/src/__tests__/Chart.test.tsx  channelWindow.test.ts
```

## Constitution Check

Principle I: the window ends at the snapshot's instant, so no bar after it is drawn into the channel.
Principle VII: one formula for the number and the picture. No violation.
