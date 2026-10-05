---
id: REQ-WP-089
title: "The chart shows a volume profile beside the price axis: volume by price level from trades, split into buy and sell (delta clustering)"
type: work-package
prd_ref: "§14.1, §27.2; owner's direction 2026-10-04"
prd_lines: "2287-2312, 4406-4421"
phase: null
status: implemented
depends_on: [REQ-WP-012, REQ-WP-083, REQ-WP-092]
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
- A profile states **how much of its window the data covers**: a 24h profile built from three hours of data says three
  hours, in words on the chart and in the response; it is never labelled 24h. (The price bins are collected from the
  moment this is deployed; there is no history before it, and none is invented from bars.)
- A block of trades whose ids show missed trades (Binance) is left out of the profile, and a profile built from bins of one
  width never mixes in rows of another.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-138-volume-profile]]
- **Tests:**
    - `tests/unit/api/test_volume_profile_route.py::test_a_profile_as_of_an_instant_uses_only_blocks_closed_by_then`
    - `tests/unit/api/test_volume_profile_route.py::test_a_profile_from_three_hours_of_data_says_so_and_is_not_complete`
    - `tests/unit/api/test_volume_profile_route.py::test_a_window_other_than_4h_24h_or_7d_is_refused[1d]`
    - `tests/unit/api/test_volume_profile_route.py::test_a_window_other_than_4h_24h_or_7d_is_refused[24]`
    - `tests/unit/api/test_volume_profile_route.py::test_a_window_other_than_4h_24h_or_7d_is_refused[5m]`
    - `tests/unit/api/test_volume_profile_route.py::test_a_window_other_than_4h_24h_or_7d_is_refused[]`
    - `tests/unit/api/test_volume_profile_route.py::test_a_window_the_data_fills_is_complete_and_uses_only_the_window`
    - `tests/unit/api/test_volume_profile_route.py::test_no_bins_is_a_404_with_a_reason_never_an_empty_profile`
    - `tests/unit/api/test_volume_profile_route.py::test_rows_of_another_width_are_left_out_and_counted`
    - `tests/unit/api/test_volume_profile_route.py::test_the_lakehouse_repository_and_the_in_memory_one_serve_the_same_profile`
    - `tests/unit/api/test_volume_profile_route.py::test_the_profile_carries_its_bins_poc_value_area_instant_width_and_coverage`
    - `tests/unit/api/test_volume_profile_route.py::test_without_an_instant_the_latest_closed_block_is_the_instant`
    - `tests/unit/pipeline/test_ingest_bins.py::test_a_daemon_without_a_bin_builder_collects_nothing_and_does_not_fail`
    - `tests/unit/pipeline/test_ingest_bins.py::test_a_trade_reaches_the_bin_builder_beside_the_bar_builder`
    - `tests/unit/pipeline/test_ingest_bins.py::test_the_bars_are_unchanged_by_collecting_bins`
    - `tests/unit/pipeline/test_ingest_bins.py::test_the_flush_commits_the_bins_with_the_bars`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_bad_width_stops_the_daemon_naming_the_variable[binance:BTCUSDT=0]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_bad_width_stops_the_daemon_naming_the_variable[binance:BTCUSDT=x]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_bad_width_stops_the_daemon_naming_the_variable[binance:BTCUSDT]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_block_length_that_is_not_a_whole_number_of_minutes_stops_the_daemon[-60]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_block_length_that_is_not_a_whole_number_of_minutes_stops_the_daemon[0]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_block_length_that_is_not_a_whole_number_of_minutes_stops_the_daemon[30]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_block_length_that_is_not_a_whole_number_of_minutes_stops_the_daemon[90]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_a_block_length_that_is_not_a_whole_number_of_minutes_stops_the_daemon[abc]`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_the_widths_and_the_block_length_are_read_from_the_environment`
    - `tests/unit/pipeline/test_ingest_profile_settings.py::test_unset_means_each_symbol_derives_its_own_width_and_the_block_is_five_minutes`
    - `tests/unit/tables/test_volume_bins.py::test_a_read_as_of_an_instant_returns_only_blocks_closed_at_or_before_it`
    - `tests/unit/tables/test_volume_bins.py::test_a_read_since_an_instant_leaves_out_earlier_blocks`
    - `tests/unit/tables/test_volume_bins.py::test_every_bin_of_a_block_is_a_row_and_reads_back_exactly`
    - `tests/unit/tables/test_volume_bins.py::test_rows_of_two_widths_are_never_mixed_the_latest_width_is_used_and_the_rest_are_counted`
    - `tests/unit/tables/test_volume_bins.py::test_series_do_not_see_each_others_rows_and_nothing_gives_an_empty_read`
    - `tests/unit/tables/test_volume_bins.py::test_the_sink_buffers_until_it_is_flushed_and_flushes_nothing_when_empty`
    - `tests/unit/volume/test_bins.py::test_a_block_is_written_once_and_a_late_trade_for_it_is_discarded_and_counted`
    - `tests/unit/volume/test_bins.py::test_a_block_that_is_still_forming_is_not_written`
    - `tests/unit/volume/test_bins.py::test_a_block_waits_out_the_grace_period_before_it_closes`
    - `tests/unit/volume/test_bins.py::test_a_block_whose_ids_show_missed_trades_is_dropped_and_counted_for_a_sequential_venue`
    - `tests/unit/volume/test_bins.py::test_a_complete_block_of_a_sequential_venue_and_any_block_of_another_are_written`
    - `tests/unit/volume/test_bins.py::test_a_price_exactly_on_a_bin_edge_falls_in_the_upper_bin`
    - `tests/unit/volume/test_bins.py::test_a_trade_on_a_block_boundary_belongs_to_the_block_that_opens_there`
    - `tests/unit/volume/test_bins.py::test_each_bin_holds_the_buy_sell_and_unknown_volume_of_its_trades_by_aggressor_side`
    - `tests/unit/volume/test_bins.py::test_ids_that_are_not_numbers_cannot_be_checked_and_do_not_drop_a_block`
    - `tests/unit/volume/test_bins.py::test_the_default_width_is_two_basis_points_of_the_price_rounded_to_one_two_or_five[0.5-0.0001]`
    - `tests/unit/volume/test_bins.py::test_the_default_width_is_two_basis_points_of_the_price_rounded_to_one_two_or_five[1-0.0002]`
    - `tests/unit/volume/test_bins.py::test_the_default_width_is_two_basis_points_of_the_price_rounded_to_one_two_or_five[150-0.02]`
    - `tests/unit/volume/test_bins.py::test_the_default_width_is_two_basis_points_of_the_price_rounded_to_one_two_or_five[2700-0.5]`
    - `tests/unit/volume/test_bins.py::test_the_default_width_is_two_basis_points_of_the_price_rounded_to_one_two_or_five[85000-20]`
    - `tests/unit/volume/test_bins.py::test_the_same_trades_in_any_order_within_the_grace_period_give_the_same_block`
    - `tests/unit/volume/test_bins.py::test_the_width_is_derived_from_the_first_trades_price_and_kept`
    - `tests/unit/volume/test_bins.py::test_the_widths_configuration_is_read_per_symbol_and_refuses_what_is_wrong_by_name`
    - `tests/unit/volume/test_profile_from_bins.py::test_blocks_are_summed_per_bin_across_time`
    - `tests/unit/volume/test_profile_from_bins.py::test_no_bins_is_refused_rather_than_an_empty_profile`
    - `tests/unit/volume/test_profile_from_bins.py::test_one_bin_is_a_valid_profile_and_says_the_value_area_is_the_whole_of_it`
    - `tests/unit/volume/test_profile_from_bins.py::test_the_profile_from_stored_bins_equals_the_profile_from_the_trades`
    - `tests/unit/volume/test_profile_from_bins.py::test_unknown_volume_counts_to_the_bin_and_to_neither_side`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[App.tsx]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[Chart.tsx]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[ProfileControls.tsx]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[api.ts]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[profilePrimitive.ts]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[profileView.ts]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_every_module_this_requirement_touches_names_it[profileWindows.ts]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_there_is_a_live_screenshot_of_each_window_in_each_scheme[24h-dark]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_there_is_a_live_screenshot_of_each_window_in_each_scheme[24h-light]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_there_is_a_live_screenshot_of_each_window_in_each_scheme[4h-dark]`
    - `tests/unit/web/test_volume_profile_artifacts.py::test_there_is_a_live_screenshot_of_each_window_in_each_scheme[4h-light]`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/ProfileControls.tsx`
    - `apps/web/src/__tests__/appProfile.test.tsx`
    - `apps/web/src/__tests__/chartProfile.test.tsx`
    - `apps/web/src/__tests__/profileControls.test.tsx`
    - `apps/web/src/__tests__/profileGeometry.test.ts`
    - `apps/web/src/__tests__/profilePrimitive.test.ts`
    - `apps/web/src/__tests__/volumeProfileApi.test.ts`
    - `apps/web/src/api.ts`
    - `apps/web/src/profilePrimitive.ts`
    - `apps/web/src/profileView.ts`
    - `apps/web/src/profileWindows.ts`
    - `src/channelflow/api/lakehouse_repository.py`
    - `src/channelflow/api/repositories.py`
    - `src/channelflow/api/volume_profile.py`
    - `src/channelflow/pipeline/ingest.py`
    - `src/channelflow/pipeline/ingest_main.py`
    - `src/channelflow/tables/volume_bins.py`
    - `src/channelflow/volume/bins.py`
    - `src/channelflow/volume/profile.py`
- **Outcomes:** [[OUT-2026-10-04-implement-volume-profile]], [[OUT-2026-10-04-plan-volume-profile]], [[OUT-2026-10-04-spec-volume-profile]], [[OUT-2026-10-04-tasks-volume-profile]]
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
