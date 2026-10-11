---
id: REQ-WP-094
title: "The liquidations pane is fed by each venue's public liquidation stream"
type: work-package
prd_ref: "§10.5, §16.4, §27.3; owner's direction 2026-10-11"
prd_lines: "919-931, 2497-2507, 4423-4436"
phase: null
status: tested
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
3. **The worker writes three liquidation features per bar**, as of the bar's close, over the trailing five
   minutes: `liquidation_long_usd_5m`, `liquidation_short_usd_5m` and `liquidation_imbalance_5m` (the pane).
   **Not delivered, and said so**: `liquidation_intensity_5m` (it needs the trailing five minutes' traded volume,
   which a bar of another timeframe does not carry) and `time_since_liquidation_spike` (it needs a per-symbol
   threshold nobody has chosen). No pane reads either; they stay registered with their library functions, and
   their registrations say they are not produced.

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
- **Tests:**
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_forced_buy_is_a_short_that_was_liquidated`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_forced_sell_is_a_long_that_was_liquidated`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_frame_that_cannot_be_read_is_refused_with_a_reason[order0]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_frame_that_cannot_be_read_is_refused_with_a_reason[order1]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_frame_that_cannot_be_read_is_refused_with_a_reason[order2]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_frame_that_cannot_be_read_is_refused_with_a_reason[order3]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_a_recorded_frame_parses`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_event_is_the_filled_quantity_at_the_average_price_at_the_venues_time`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_falls_back_to_the_order_price_and_quantity_when_nothing_filled_is_reported`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_frames_that_are_not_liquidations_are_ignored_not_errors[frame0]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_frames_that_are_not_liquidations_are_ignored_not_errors[frame1]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_frames_that_are_not_liquidations_are_ignored_not_errors[frame2]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_binance_only_the_symbols_asked_for_are_returned`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_buy_update_is_a_long_that_was_liquidated`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_frame_with_several_events_gives_several`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_row_that_cannot_be_read_is_refused_with_a_reason[row0]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_row_that_cannot_be_read_is_refused_with_a_reason[row1]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_row_that_cannot_be_read_is_refused_with_a_reason[row2]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_row_that_cannot_be_read_is_refused_with_a_reason[row3]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_a_sell_update_is_a_short_that_was_liquidated`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_event_fields_and_times`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_only_the_symbols_asked_for_are_returned`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_bybit_subscription_acknowledgements_and_other_topics_are_ignored`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_closing_buy_of_a_short_position_is_a_short_that_was_liquidated`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_closing_sell_of_a_long_position_is_a_long_that_was_liquidated`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_combination_that_contradicts_itself_is_unknown_not_guessed`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_contract_size_we_do_not_know_refuses_the_event_rather_than_guessing`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_detail_that_cannot_be_read_is_refused_with_a_reason[detail0]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_detail_that_cannot_be_read_is_refused_with_a_reason[detail1]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_detail_that_cannot_be_read_is_refused_with_a_reason[detail2]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_a_detail_that_cannot_be_read_is_refused_with_a_reason[detail3]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_acknowledgements_and_other_channels_are_ignored`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_every_recorded_frame_for_a_watched_instrument_parses`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_in_net_mode_the_closing_orders_side_gives_the_position[net-buy-short_liquidated]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_in_net_mode_the_closing_orders_side_gives_the_position[net-sell-long_liquidated]`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_instruments_not_watched_are_ignored`
    - `tests/unit/connectors/test_context_liquidation_parsers.py::test_okx_size_is_contracts_and_is_converted_to_base_units`
    - `tests/unit/context/test_liquidation_stream.py::test_a_bare_pong_is_neither_stored_nor_counted_as_a_failure`
    - `tests/unit/context/test_liquidation_stream.py::test_a_frame_for_a_symbol_not_watched_is_not_stored`
    - `tests/unit/context/test_liquidation_stream.py::test_a_frame_that_is_not_json_is_counted_and_the_next_is_still_stored`
    - `tests/unit/context/test_liquidation_stream.py::test_a_heartbeat_is_stored_for_every_symbol_watched_when_a_minute_is_covered`
    - `tests/unit/context/test_liquidation_stream.py::test_a_liquidation_stream_that_says_nothing_for_ten_minutes_is_not_reconnected`
    - `tests/unit/context/test_liquidation_stream.py::test_a_recorded_binance_frame_becomes_a_stored_event_for_a_watched_symbol`
    - `tests/unit/context/test_liquidation_stream.py::test_an_unknown_venue_has_no_liquidation_stream`
    - `tests/unit/context/test_liquidation_stream.py::test_binance_uses_the_market_path_of_the_futures_websocket_not_the_legacy_one`
    - `tests/unit/context/test_liquidation_stream.py::test_bybit_subscribes_to_one_topic_per_symbol_on_the_linear_socket`
    - `tests/unit/context/test_liquidation_stream.py::test_every_recorded_okx_frame_for_a_watched_instrument_is_stored`
    - `tests/unit/context/test_liquidation_stream.py::test_okx_contract_values_are_asked_for_through_the_poller_and_none_when_they_cannot_be`
    - `tests/unit/context/test_liquidation_stream.py::test_okx_subscribes_to_the_swap_liquidation_channel`
    - `tests/unit/context/test_liquidation_stream.py::test_okx_with_no_contract_value_refuses_its_events_and_counts_them`
    - `tests/unit/context/test_liquidation_stream.py::test_the_collector_steps_its_streams_and_commits_their_sink_with_the_polls`
    - `tests/unit/context/test_streams.py::test_a_dead_reader_writes_no_heartbeat`
    - `tests/unit/context/test_streams.py::test_a_dead_reader_writes_no_heartbeat_while_the_session_is_still_throttled`
    - `tests/unit/context/test_streams.py::test_a_frame_the_handler_cannot_read_is_counted_and_the_next_one_is_still_handled`
    - `tests/unit/context/test_streams.py::test_a_heartbeat_is_written_for_each_minute_the_connection_stayed_up`
    - `tests/unit/context/test_streams.py::test_a_heartbeat_is_written_once_per_minute_however_often_the_task_steps`
    - `tests/unit/context/test_streams.py::test_a_quiet_stream_is_not_reconnected_for_being_quiet`
    - `tests/unit/context/test_streams.py::test_a_reconnect_inside_a_minute_uncovers_that_minute`
    - `tests/unit/context/test_streams.py::test_an_unknown_venue_has_no_stream_policy`
    - `tests/unit/context/test_streams.py::test_every_frame_reaches_the_handler_with_the_time_it_was_received`
    - `tests/unit/context/test_streams.py::test_frames_that_keep_arriving_keep_a_busy_streams_silence_limit_from_firing`
    - `tests/unit/context/test_streams.py::test_the_minute_in_which_the_connection_was_made_is_not_covered`
    - `tests/unit/context/test_streams.py::test_the_silence_limit_is_disabled_for_a_quiet_stream_but_the_keepalive_is_not`
    - `tests/unit/features/test_context_registrations.py::test_the_imbalance_says_it_is_absent_for_a_window_nobody_watched`
    - `tests/unit/features/test_context_registrations.py::test_the_liquidation_sums_say_zero_needs_a_stream_that_was_listening`
    - `tests/unit/features/test_context_registrations.py::test_the_two_liquidation_features_the_worker_does_not_write_say_so[liquidation_intensity_5m]`
    - `tests/unit/features/test_context_registrations.py::test_the_two_liquidation_features_the_worker_does_not_write_say_so[time_since_liquidation_spike]`
    - `tests/unit/features/test_liquidation_values.py::test_a_covered_quiet_window_has_zero_sums_and_no_imbalance`
    - `tests/unit/features/test_liquidation_values.py::test_a_window_the_stream_did_not_cover_writes_nothing_even_with_events_inside_it`
    - `tests/unit/features/test_liquidation_values.py::test_an_event_dated_after_the_close_by_a_fast_venue_clock_is_not_used`
    - `tests/unit/features/test_liquidation_values.py::test_appending_later_events_and_heartbeats_changes_nothing`
    - `tests/unit/features/test_liquidation_values.py::test_events_delivered_after_the_close_are_not_used`
    - `tests/unit/features/test_liquidation_values.py::test_every_minute_of_the_window_needs_its_heartbeat`
    - `tests/unit/features/test_liquidation_values.py::test_the_sums_and_the_imbalance_are_the_librarys_over_the_trailing_five_minutes`
    - `tests/unit/features/test_liquidation_values.py::test_the_window_is_open_at_the_start_and_closed_at_the_close`
    - `tests/unit/features/test_liquidation_values.py::test_two_heartbeats_in_one_minute_do_not_stand_in_for_two_minutes`
    - `tests/unit/features/test_liquidation_values.py::test_unknown_side_events_are_in_neither_sum`
    - `tests/unit/pipeline/test_context_main.py::test_an_unknown_stream_is_refused_naming_the_known_ones`
    - `tests/unit/pipeline/test_context_main.py::test_the_liquidation_stream_runs_by_default_and_can_be_turned_off`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_a_bar_the_stream_did_not_cover_gets_no_liquidation_feature`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_a_quiet_covered_bar_has_zero_sums_and_no_imbalance_row`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_a_second_pass_writes_nothing_more`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_a_series_with_no_perpetual_gets_no_liquidation_features`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_an_event_delivered_after_the_close_is_not_in_the_bar`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_derivatives_and_liquidations_are_one_commit`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_one_series_failing_in_the_liquidation_step_is_reported_and_the_others_go_on`
    - `tests/unit/pipeline/test_context_pass_liquidations.py::test_the_pass_writes_the_three_liquidation_features_for_covered_bars`
    - `tests/unit/tables/test_liquidations.py::test_a_heartbeat_already_stored_is_recognised_by_a_new_sink`
    - `tests/unit/tables/test_liquidations.py::test_a_heartbeat_has_no_side_price_or_quantity_and_round_trips`
    - `tests/unit/tables/test_liquidations.py::test_a_heartbeat_is_stored_once_per_symbol_per_minute`
    - `tests/unit/tables/test_liquidations.py::test_an_empty_flush_commits_nothing_and_a_flush_clears_the_buffer`
    - `tests/unit/tables/test_liquidations.py::test_an_event_and_a_heartbeat_at_the_same_instant_do_not_collide`
    - `tests/unit/tables/test_liquidations.py::test_an_event_round_trips_exactly_with_decimals`
    - `tests/unit/tables/test_liquidations.py::test_events_and_heartbeats_are_read_back_by_market_and_sorted`
    - `tests/unit/tables/test_liquidations.py::test_the_schema_is_section_10_5_plus_the_kind_and_both_times`
    - `tests/unit/tables/test_liquidations.py::test_the_sink_stores_an_event_once_even_if_the_venue_replays_it_after_a_reconnect`
    - `tests/unit/tables/test_liquidations.py::test_two_events_that_differ_in_any_identifying_field_are_two_events[different0]`
    - `tests/unit/tables/test_liquidations.py::test_two_events_that_differ_in_any_identifying_field_are_two_events[different1]`
    - `tests/unit/tables/test_liquidations.py::test_two_events_that_differ_in_any_identifying_field_are_two_events[different2]`
    - `tests/unit/tables/test_liquidations.py::test_two_events_that_differ_in_any_identifying_field_are_two_events[different3]`
    - `tests/unit/tables/test_liquidations.py::test_two_events_that_differ_in_any_identifying_field_are_two_events[different4]`
    - `tests/unit/tables/test_liquidations.py::test_two_events_that_differ_in_any_identifying_field_are_two_events[different5]`
- **Outcomes:** [[OUT-2026-10-11-implement-liquidations-collector]], [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

A liquidation stream is event-driven and sparse for the smaller symbols. A pane that is empty because nothing
liquidated in the range is a correct answer and must be distinguishable from one that is empty because nothing
was listening; the heartbeat rule above is what makes it so.
