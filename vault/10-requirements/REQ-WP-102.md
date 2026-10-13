---
id: REQ-WP-102
title: "The chart is live: the bars the ingest is still holding reach the browser over a WebSocket, at 1m, without waiting for the table"
type: work-package
prd_ref: "§28.7, §6.3, §27; owner's direction 2026-10-13"
prd_lines: "4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-066, REQ-WP-068, REQ-WP-042, REQ-API-001, REQ-WP-092]
tags: [live, websocket, redpanda, chart, bars]
hard_gated: false
---

## Requirement

The bars table is written fifteen bars at a time ([[REQ-WP-068]]: fewer commits keep the file count and the read cost
down), so a one-minute chart read from the API is up to fifteen minutes behind. On 2026-10-13 the owner decided how to
solve it: **what goes into the bars table is one thing, and the chart gets its own real-time feed**; the live feed is at
**1m**, proxied to the browser over a WebSocket.

1. **The ingest publishes what it holds.** Each ingest daemon publishes its **forming** 1m bar (at most once a second) and
   each **final** 1m bar to the event backbone (Redpanda, [[REQ-WP-042]]) on a versioned topic keyed `venue:symbol`. It is
   best effort: a broker that is down or slow is counted and the ingest carries on, because the bars table is the record
   and this is a view.
2. **The API relays it.** The read API consumes that topic, keeps the last thirty minutes of 1m bars per series, and
   delivers them on a WebSocket at `/api/v1/live` -- the §28.7 socket ([[REQ-API-001]]) under the one prefix the public proxy reaches: on subscribing to `bars` at `1m` the subscriber
   first receives the cached bars (the stretch the table has not caught up on), then every update as it happens. A final bar
   is never replaced by a forming one for the same minute.
   **The socket is gated like everything under `/api/v1/`.** The Telegram gate used to close every browser websocket (a header
   cannot be set on one and a URL is logged); the live socket takes the launch data as a **subprotocol** (`tma`, then the
   data base64url-encoded), is closed (1008) without a valid one, and answers with the scheme only. `/ws/market` stays
   closed to the browser when authentication is required.
3. **The chart uses it.** On the 1m timeframe the page opens the socket, draws the live bars after the last stored one,
   updates the forming candle in place (no redraw of the chart, no change of the reader's zoom), extends the panes' time
   axis so they stay aligned, shows the Volume pane live, says whether it is **live** or **delayed**, reconnects with
   backoff, and falls back to the periodic reload when the socket is down. Panes whose values the worker computes (OFI,
   open interest, ...) are not live and are not drawn as if they were.
4. **A forming bar is not a bar.** It is marked `is_final: false` all the way, is never stored, and no feature reads it
   (Principle I): this feed is for looking, not for computing.

Timeframes above 1m keep the periodic reload in this requirement; their forming bucket is a follow-up.

## Acceptance

- The builder exposes its forming bars without changing them (tests); a bar is the same whether read forming and then
  final or only final.
- A published record carries the bar as the REST bars do (nanosecond instants as strings), `is_final`, the venue and
  symbol, and is keyed `venue:symbol` (tests on a recorded round trip over the in-process transport).
- A broker that raises on publish does not stop the ingest, and the failures are counted (test).
- The relay's cache keeps the newest thirty minutes, replaces a forming bar by a later forming or final one, never a
  final by a forming one, and delivers its snapshot before the first update to a new subscriber (tests).
- A subscriber for another series or timeframe receives nothing (test); a subscription at a timeframe other than 1m is
  acknowledged as not live.
- With authentication required the live socket is closed without launch data, with data that does not verify and with
  signed data under another scheme name, accepts signed data and echoes only `tma`; `/ws/market` stays closed; the public
  proxy still has exactly one location (tests).
- The web: the live bars are merged after the stored ones; a stored bar for a minute supersedes the live one; the candle is
  updated in place; the panes' axis has the same bars; the state is shown; the socket is reopened after it drops (tests).
- On the running stack the last bar of the 1m chart is less than five seconds old, from a browser, with the ingest
  committing fifteen at a time.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-154-live-bars]]
- **Tests:**
    - `tests/integration/test_live_on_redpanda.py::test_a_bar_published_before_the_consumer_arrived_is_still_relayed`
    - `tests/integration/test_live_on_redpanda.py::test_the_topic_is_created_with_the_cache_windows_retention`
    - `tests/unit/api/test_telegram_gate.py::test_launch_data_that_is_too_old_is_refused_on_the_live_socket_too`
    - `tests/unit/api/test_telegram_gate.py::test_signed_launch_data_under_another_scheme_name_is_not_accepted_on_the_live_socket`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_accepts_signed_launch_data_and_answers_with_the_scheme_only`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_is_refused_without_launch_data_when_authentication_is_required`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_refuses_launch_data_that_does_not_verify[no-token]`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_refuses_launch_data_that_does_not_verify[not-base64]`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_refuses_launch_data_that_does_not_verify[unsigned]`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_refuses_launch_data_that_does_not_verify[wrong-scheme]`
    - `tests/unit/api/test_telegram_gate.py::test_the_live_socket_works_without_a_subprotocol_when_authentication_is_off`
    - `tests/unit/api/test_telegram_gate.py::test_the_original_socket_stays_closed_when_authentication_is_required`
    - `tests/unit/api/test_ws_live.py::test_a_one_minute_bars_subscription_is_acknowledged_as_live_and_gets_the_cache_first[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_a_one_minute_bars_subscription_is_acknowledged_as_live_and_gets_the_cache_first[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_a_published_bar_reaches_the_subscriber_of_that_series_and_not_another[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_a_published_bar_reaches_the_subscriber_of_that_series_and_not_another[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_a_record_on_the_topic_reaches_a_subscriber_through_the_relay[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_a_record_on_the_topic_reaches_a_subscriber_through_the_relay[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_a_socket_that_has_gone_away_does_not_stop_the_others[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_a_socket_that_has_gone_away_does_not_stop_the_others[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_a_subscriber_to_other_signals_only_gets_no_snapshot[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_a_subscriber_to_other_signals_only_gets_no_snapshot[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_a_subscription_at_another_timeframe_is_acknowledged_as_not_live_and_gets_no_snapshot[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_a_subscription_at_another_timeframe_is_acknowledged_as_not_live_and_gets_no_snapshot[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_an_api_whose_broker_is_unreachable_still_serves_and_says_the_feed_is_empty[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_an_api_whose_broker_is_unreachable_still_serves_and_says_the_feed_is_empty[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_an_app_with_no_live_feed_says_so[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_an_app_with_no_live_feed_says_so[lakehouse]`
    - `tests/unit/api/test_ws_live.py::test_an_empty_cache_still_sends_an_empty_snapshot_so_the_page_knows_it_has_heard_everything[in_memory]`
    - `tests/unit/api/test_ws_live.py::test_an_empty_cache_still_sends_an_empty_snapshot_so_the_page_knows_it_has_heard_everything[lakehouse]`
    - `tests/unit/bars/test_forming.py::test_a_window_that_has_been_finalised_is_no_longer_forming`
    - `tests/unit/bars/test_forming.py::test_nothing_is_forming_before_the_first_trade`
    - `tests/unit/bars/test_forming.py::test_reading_it_changes_nothing_that_is_published_later`
    - `tests/unit/bars/test_forming.py::test_several_open_windows_come_oldest_first`
    - `tests/unit/bars/test_forming.py::test_the_open_window_is_forming_and_says_it_is_not_final`
    - `tests/unit/deploy/test_compose_logging.py::test_every_ingest_service_and_the_api_are_handed_the_broker_for_the_live_feed`
    - `tests/unit/deploy/test_compose_logging.py::test_no_ingest_waits_for_the_broker_because_the_feed_is_a_view_not_the_record`
    - `tests/unit/deploy/test_compose_logging.py::test_the_web_proxy_passes_the_websocket_upgrade_through_its_one_location`
    - `tests/unit/live/test_messages.py::test_a_bar_is_carried_as_the_rest_bars_are_with_instants_as_strings`
    - `tests/unit/live/test_messages.py::test_a_live_bar_is_a_value_two_equal_ones_compare_equal`
    - `tests/unit/live/test_messages.py::test_a_record_round_trips_field_for_field`
    - `tests/unit/live/test_messages.py::test_a_record_that_is_not_a_live_bar_is_refused_not_guessed_at`
    - `tests/unit/live/test_messages.py::test_the_ingest_time_travels_on_the_record_so_the_later_forming_bar_can_win`
    - `tests/unit/live/test_messages.py::test_the_topic_is_versioned_and_the_key_is_venue_and_symbol`
    - `tests/unit/live/test_publisher.py::test_a_broker_that_raises_stops_nothing_and_is_counted`
    - `tests/unit/live/test_publisher.py::test_a_failure_is_not_remembered_as_a_publish_for_the_throttle`
    - `tests/unit/live/test_publisher.py::test_a_final_bar_does_not_wait_for_the_forming_throttle_of_the_next_minute`
    - `tests/unit/live/test_publisher.py::test_a_final_bar_is_always_published_even_inside_the_second`
    - `tests/unit/live/test_publisher.py::test_a_forming_bar_is_published_to_the_live_topic_keyed_by_series`
    - `tests/unit/live/test_publisher.py::test_a_publisher_with_no_broker_publishes_nothing_and_says_so`
    - `tests/unit/live/test_publisher.py::test_each_series_is_throttled_on_its_own`
    - `tests/unit/live/test_publisher.py::test_forming_bars_are_published_at_most_once_a_second`
    - `tests/unit/live/test_relay.py::test_a_bar_exactly_at_the_edge_of_the_window_is_kept`
    - `tests/unit/live/test_relay.py::test_a_final_bar_replaces_a_forming_one`
    - `tests/unit/live/test_relay.py::test_a_first_bar_is_kept_and_forwarded`
    - `tests/unit/live/test_relay.py::test_a_forming_bar_never_replaces_a_final_one_however_late_it_was_ingested`
    - `tests/unit/live/test_relay.py::test_a_later_forming_bar_replaces_an_earlier_one_for_the_same_minute`
    - `tests/unit/live/test_relay.py::test_a_second_final_bar_for_a_minute_does_not_amend_the_first`
    - `tests/unit/live/test_relay.py::test_an_older_forming_bar_arriving_late_is_ignored_and_not_forwarded`
    - `tests/unit/live/test_relay.py::test_bars_older_than_the_window_behind_the_newest_are_dropped`
    - `tests/unit/live/test_relay.py::test_the_relay_reads_the_topic_caches_and_forwards_only_what_changed`
    - `tests/unit/live/test_relay.py::test_the_relay_survives_a_record_it_cannot_read_and_counts_it`
    - `tests/unit/live/test_relay.py::test_the_snapshot_is_oldest_first_and_per_series`
    - `tests/unit/live/test_relay.py::test_the_window_is_thirty_minutes`
    - `tests/unit/pipeline/test_ingest_live.py::test_a_broker_that_fails_costs_the_ingest_no_trade`
    - `tests/unit/pipeline/test_ingest_live.py::test_a_daemon_without_a_live_feed_is_unchanged`
    - `tests/unit/pipeline/test_ingest_live.py::test_a_failing_live_feed_does_not_stop_the_bar_reaching_the_table`
    - `tests/unit/pipeline/test_ingest_live.py::test_a_final_bar_goes_to_the_table_sink_and_to_the_live_feed`
    - `tests/unit/pipeline/test_ingest_live.py::test_a_step_publishes_the_forming_bar_it_is_building`
    - `tests/unit/pipeline/test_ingest_live.py::test_the_published_forming_bar_is_the_one_the_builder_holds`
    - `tests/unit/pipeline/test_ingest_live.py::test_the_table_sink_is_written_first_so_the_record_comes_before_the_view`
    - `tests/unit/web/test_live_artifacts.py::test_each_vitest_file_for_the_feed_exists_and_names_the_requirement[appLive.test.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_each_vitest_file_for_the_feed_exists_and_names_the_requirement[chartLive.test.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_each_vitest_file_for_the_feed_exists_and_names_the_requirement[live.test.ts]`
    - `tests/unit/web/test_live_artifacts.py::test_each_vitest_file_for_the_feed_exists_and_names_the_requirement[useLiveBars.test.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_every_module_this_requirement_touches_names_it[App.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_every_module_this_requirement_touches_names_it[Chart.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_every_module_this_requirement_touches_names_it[LiveChip.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_every_module_this_requirement_touches_names_it[PaneChart.tsx]`
    - `tests/unit/web/test_live_artifacts.py::test_every_module_this_requirement_touches_names_it[live.ts]`
    - `tests/unit/web/test_live_artifacts.py::test_every_module_this_requirement_touches_names_it[useLiveBars.ts]`
    - `tests/unit/web/test_live_artifacts.py::test_the_feed_is_asked_for_only_by_the_one_minute_unpinned_view`
    - `tests/unit/web/test_live_artifacts.py::test_the_page_gives_the_one_feed_to_the_chart_the_pane_and_the_chip`
    - `tests/unit/web/test_live_artifacts.py::test_the_socket_goes_to_the_gated_path_under_the_one_proxied_prefix`
- **Code:**
    - `apps/web/src/App.tsx`
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/LiveChip.tsx`
    - `apps/web/src/PaneChart.tsx`
    - `apps/web/src/__tests__/appLive.test.tsx`
    - `apps/web/src/__tests__/chartLive.test.tsx`
    - `apps/web/src/__tests__/live.test.ts`
    - `apps/web/src/__tests__/useLiveBars.test.tsx`
    - `apps/web/src/live.ts`
    - `apps/web/src/useLiveBars.ts`
    - `src/channelflow/api/live.py`
    - `src/channelflow/api/main.py`
    - `src/channelflow/api/telegram_auth.py`
    - `src/channelflow/api/ws.py`
    - `src/channelflow/bars/builder.py`
    - `src/channelflow/live/__init__.py`
    - `src/channelflow/live/broker.py`
    - `src/channelflow/live/messages.py`
    - `src/channelflow/live/publisher.py`
    - `src/channelflow/live/relay.py`
    - `src/channelflow/pipeline/ingest.py`
    - `src/channelflow/pipeline/ingest_main.py`
- **Outcomes:** [[OUT-2026-10-13-implement-live-bars]], [[OUT-2026-10-13-spec-live-bars]]
<!-- trace:end -->
