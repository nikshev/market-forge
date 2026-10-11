---
id: REQ-WP-093
title: "The open-interest, funding and basis panes are fed by a collector that polls each venue's public derivatives data"
type: work-package
prd_ref: "§10.4, §16.1, §16.2, §16.3, §27.3; owner's direction 2026-10-11"
prd_lines: "903-918, 2460-2496, 4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-030, REQ-WP-084, REQ-WP-013]
tags: [derivatives, open-interest, funding, basis, collector, panes]
hard_gated: false
---

## Requirement

On 2026-10-11 the owner looked at the lower-pane row of a chart and saw `Open interest`, `Funding (z)` and
`Basis (bps)` all reading "no data". They asked why, and then asked for every pane to show data.

Read from the code and measured against the running stack: the three features are registered
([[REQ-WP-013]]), the pure functions exist (`derivatives/openinterest.py`, `derivatives/funding.py`) and the
panes exist ([[REQ-WP-030]]), but **nothing produces a `DerivativesState`** (PRD §10.4). The connectors'
`derivatives_state` normalizers have no caller, no table stores their output, and the worker writes only the six
trade-derived features. A pane naming a feature nobody records says "no data" for ever, which is what
[[REQ-WP-084]] made honest and not what the owner wants to see.

This requirement builds the missing producer, end to end, for the venues the deployment already ingests
(Binance, Bybit, OKX):

1. **A collector service** (`context`, one per venue, a compose service on the same image) polls the venue's
   public REST endpoints on a fixed cadence and stores each answer as a `DerivativesState` row in a new
   append-only lakehouse table. It holds no keys. Measured 2026-10-11 from this host: every endpoint below
   answers, and the futures websocket streams the older code comment called unreachable do connect.
   - Binance USD-M futures: `premiumIndex` (mark, index, last funding rate, next funding time),
     `futures/data/openInterestHist` for the open interest **in USD as the venue reports it** (the base-unit
     `openInterest` endpoint is not used for USD: `oi_series` skips base-only states on purpose, because
     multiplying by a price of our choosing would invent a figure the venue did not report).
   - Bybit linear: `tickers` (mark, index, funding, next funding, `openInterestValue` in USD).
   - OKX swap: `open-interest` (`oiUsd`), `funding-rate`, `mark-price`, and the index ticker.
2. **Funding history is loaded once, from each venue's own public history endpoint**, because
   `funding_z` is a 24-settled-interval z-score ([[ADR-026]]: it refuses on fewer) and a venue settles every
   8 hours, so waiting would mean eight days of "no data". A settled rate is public at its settlement time, so
   a history row is a row that existed then: it enters the table with `event_time = settlement time` and is
   tagged as loaded from history, never as polled.
3. **The worker writes the three features per bar, as of the bar's close**, into `feature_snapshots` for every
   (venue, symbol, timeframe) series that has bars, for every timeframe. Rules that hold:
   - **No look-ahead** (Principle I, [[REQ-BIAS-005]]): the value at a bar's close uses only states with
     `event_time <= close`, and only settled funding rates (`settled_funding` is the guard).
   - **Freshness is stated, not inferred**: a state older than the staleness bound is not presented as the value
     now (`require_fresh`). The bound for the polled values is a few poll intervals; for funding the *settlement*
     is allowed to be as old as one interval plus a margin, because a settlement is an 8-hour event and the
     library's 5-minute default would make `funding_z` exist for five minutes in eight hours.
   - **Absence, not zero** ([[REQ-WP-084]]): where a value cannot be computed (collector down, too few settled
     rates, constant series) no row is written, and the pane says so.
   - **A spot series is given its own venue's perpetual**: the Binance series is a spot market and the
     derivatives are the same venue's perpetual of the same pair. This association is stated in the feature's
     source and in the docs, not hidden. `basis_bps` is the perpetual's mark against the venue's index (its spot
     composite).
4. **The deployment runs it**: compose services for the three venues, a health signal, a Prometheus metric for
   the age of the last state, retention through the existing maintenance service, and a section in
   `docs/deployment.md`.

**Not in this requirement**: liquidations ([[REQ-WP-094]]), the order book ([[REQ-WP-095]]), long/short ratios
(§16.5 is "optional when reliable/public"), and cross-venue funding dispersion.

## Acceptance

- A table `derivatives_state` stores `DerivativesState` as §10.4 defines it, append-only, with prices as
  decimals, event time and ingest time kept apart (Principle II), and a column saying whether the row was polled
  or loaded from history.
- For recorded responses of each of the three venues the normalizers produce the expected states, including the
  USD open interest the venue reports; a response missing a field yields a state with that field absent, never a
  default.
- The collector tolerates a failed or rate-limited poll: it records nothing for it, logs it, retries on the next
  cycle, and never writes the previous value again as if it were new. A test with a failing client shows it.
- The history load is idempotent: running it twice stores each settlement once.
- For a stored fixture of states, the writer's `open_interest_usd`, `funding_z` and `basis_bps` at a bar's close
  equal the library functions' values at that instant, are unchanged when states with `event_time` after the
  close are appended (a test), and are absent where the library refuses.
- On the running stack, within one worker cycle after the collector has run for a day, `GET
  /api/v1/features/timeseries` for Binance, Bybit and OKX BTC carries `open_interest_usd`, `funding_z` and
  `basis_bps` at the viewed timeframes, and the three panes are enabled. The check is a recorded query, not a
  claim.
- The existing six trade features are unchanged in value and in count.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-145-derivatives-collector]]
- **Tests:**
    - `tests/unit/connectors/test_context_derivatives.py::test_a_history_row_with_no_rate_is_refused_not_stored_as_zero[binance]`
    - `tests/unit/connectors/test_context_derivatives.py::test_a_history_row_with_no_rate_is_refused_not_stored_as_zero[bybit]`
    - `tests/unit/connectors/test_context_derivatives.py::test_a_history_row_with_no_rate_is_refused_not_stored_as_zero[okx]`
    - `tests/unit/connectors/test_context_derivatives.py::test_binance_mark_index_and_funding_come_from_premium_index_at_the_venues_time`
    - `tests/unit/connectors/test_context_derivatives.py::test_binance_open_interest_usd_is_the_figure_the_venue_reports_at_the_buckets_time`
    - `tests/unit/connectors/test_context_derivatives.py::test_binance_state_refuses_an_answer_missing_a_field_rather_than_defaulting_it`
    - `tests/unit/connectors/test_context_derivatives.py::test_bybit_state_is_stamped_with_the_responses_time_not_the_receipt`
    - `tests/unit/connectors/test_context_derivatives.py::test_bybit_state_without_a_venue_time_keeps_its_old_behaviour`
    - `tests/unit/connectors/test_context_derivatives.py::test_every_venues_history_becomes_one_settled_row_per_settlement[binance-<lambda>-raw0-fundingTime]`
    - `tests/unit/connectors/test_context_derivatives.py::test_every_venues_history_becomes_one_settled_row_per_settlement[bybit-<lambda>-raw1-fundingRateTimestamp]`
    - `tests/unit/connectors/test_context_derivatives.py::test_every_venues_history_becomes_one_settled_row_per_settlement[okx-<lambda>-raw2-fundingTime]`
    - `tests/unit/connectors/test_context_derivatives.py::test_okx_contract_value_is_read_from_the_instruments_answer_not_assumed`
    - `tests/unit/connectors/test_context_derivatives.py::test_okx_contract_value_refuses_an_instrument_the_answer_does_not_contain`
    - `tests/unit/connectors/test_context_derivatives.py::test_okx_history_uses_the_realized_rate_not_the_formula_rate`
    - `tests/unit/context/test_pollers.py::test_a_failing_history_request_is_a_failure_and_stores_nothing`
    - `tests/unit/context/test_pollers.py::test_a_poll_with_one_failing_request_returns_nothing_at_all[binance-BTCUSDT-/fapi/v1/premiumIndex]`
    - `tests/unit/context/test_pollers.py::test_a_poll_with_one_failing_request_returns_nothing_at_all[binance-BTCUSDT-/futures/data/openInterestHist]`
    - `tests/unit/context/test_pollers.py::test_a_poll_with_one_failing_request_returns_nothing_at_all[bybit-BTCUSDT-/v5/market/tickers]`
    - `tests/unit/context/test_pollers.py::test_a_poll_with_one_failing_request_returns_nothing_at_all[okx-BTC-USDT-SWAP-/api/v5/public/mark-price]`
    - `tests/unit/context/test_pollers.py::test_a_poll_with_one_failing_request_returns_nothing_at_all[okx-BTC-USDT-SWAP-/api/v5/public/open-interest]`
    - `tests/unit/context/test_pollers.py::test_a_rate_limit_is_passed_on_with_its_wait_so_the_loop_can_back_off`
    - `tests/unit/context/test_pollers.py::test_an_answer_missing_what_the_normalizer_needs_is_a_failed_poll_not_a_crash[binance-BTCUSDT-/fapi/v1/premiumIndex-markPrice]`
    - `tests/unit/context/test_pollers.py::test_an_answer_missing_what_the_normalizer_needs_is_a_failed_poll_not_a_crash[bybit-BTCUSDT-/v5/market/tickers-result]`
    - `tests/unit/context/test_pollers.py::test_an_answer_missing_what_the_normalizer_needs_is_a_failed_poll_not_a_crash[okx-BTC-USDT-SWAP-/api/v5/public/mark-price-data]`
    - `tests/unit/context/test_pollers.py::test_an_unknown_venue_is_refused_not_defaulted`
    - `tests/unit/context/test_pollers.py::test_binance_asks_for_several_open_interest_buckets_so_a_missed_poll_leaves_no_hole`
    - `tests/unit/context/test_pollers.py::test_binance_poll_is_a_state_for_mark_and_funding_and_the_recent_open_interest_buckets`
    - `tests/unit/context/test_pollers.py::test_bybit_poll_is_one_state_at_the_venues_time`
    - `tests/unit/context/test_pollers.py::test_history_asks_for_enough_settlements_to_fill_the_window[binance-BTCUSDT-fundingRate]`
    - `tests/unit/context/test_pollers.py::test_history_asks_for_enough_settlements_to_fill_the_window[bybit-BTCUSDT-funding/history]`
    - `tests/unit/context/test_pollers.py::test_history_asks_for_enough_settlements_to_fill_the_window[okx-BTC-USDT-SWAP-funding-rate-history]`
    - `tests/unit/context/test_pollers.py::test_history_is_one_settled_row_per_settlement[binance-BTCUSDT]`
    - `tests/unit/context/test_pollers.py::test_history_is_one_settled_row_per_settlement[bybit-BTCUSDT]`
    - `tests/unit/context/test_pollers.py::test_history_is_one_settled_row_per_settlement[okx-BTC-USDT-SWAP]`
    - `tests/unit/context/test_pollers.py::test_okx_asks_for_the_contract_value_once_per_symbol`
    - `tests/unit/context/test_pollers.py::test_okx_poll_assembles_four_answers_with_the_contract_value_it_fetched`
    - `tests/unit/context/test_rest.py::test_a_rate_limit_carries_how_long_the_venue_asked_us_to_wait[418]`
    - `tests/unit/context/test_rest.py::test_a_rate_limit_carries_how_long_the_venue_asked_us_to_wait[429]`
    - `tests/unit/context/test_rest.py::test_a_rate_limit_without_a_retry_after_waits_a_stated_minimum`
    - `tests/unit/context/test_rest.py::test_a_successful_answer_is_its_decoded_json`
    - `tests/unit/context/test_rest.py::test_a_timeout_or_a_dropped_connection_is_a_failure_and_never_hangs`
    - `tests/unit/context/test_rest.py::test_an_answer_that_is_not_json_is_a_failure_not_an_exception_of_another_kind`
    - `tests/unit/context/test_rest.py::test_any_other_failure_status_is_a_failure_naming_the_status[400]`
    - `tests/unit/context/test_rest.py::test_any_other_failure_status_is_a_failure_naming_the_status[403]`
    - `tests/unit/context/test_rest.py::test_any_other_failure_status_is_a_failure_naming_the_status[500]`
    - `tests/unit/context/test_rest.py::test_any_other_failure_status_is_a_failure_naming_the_status[503]`
    - `tests/unit/context/test_rest.py::test_the_query_parameters_are_sent`
    - `tests/unit/context/test_runtime.py::test_a_burst_of_rows_is_flushed_without_waiting_for_the_interval`
    - `tests/unit/context/test_runtime.py::test_a_failed_flush_keeps_the_rows_and_is_counted_not_fatal`
    - `tests/unit/context/test_runtime.py::test_a_failed_history_load_is_retried_on_the_poll_cadence_not_after_an_hour`
    - `tests/unit/context/test_runtime.py::test_a_failed_poll_stores_nothing_and_is_retried_on_the_next_cycle`
    - `tests/unit/context/test_runtime.py::test_a_rate_limit_delays_the_next_attempt_by_what_the_venue_asked`
    - `tests/unit/context/test_runtime.py::test_close_flushes_what_is_pending`
    - `tests/unit/context/test_runtime.py::test_history_is_refreshed_on_its_own_cadence_and_stored_once`
    - `tests/unit/context/test_runtime.py::test_nothing_is_polled_again_before_the_interval`
    - `tests/unit/context/test_runtime.py::test_pending_rows_are_flushed_on_the_flush_interval_and_not_before`
    - `tests/unit/context/test_runtime.py::test_the_first_step_loads_history_and_polls_once`
    - `tests/unit/context/test_runtime.py::test_the_previous_state_is_never_stored_again_as_if_it_were_new`
    - `tests/unit/context/test_status.py::test_a_collector_that_has_just_started_is_given_its_first_intervals`
    - `tests/unit/context/test_status.py::test_before_any_success_the_age_is_reported_as_unknown_not_zero`
    - `tests/unit/context/test_status.py::test_failures_are_counted_and_a_success_resets_the_run`
    - `tests/unit/context/test_status.py::test_healthy_means_a_success_within_three_intervals`
    - `tests/unit/context/test_status.py::test_the_endpoints_answer_200_when_healthy_and_503_when_not`
    - `tests/unit/context/test_status.py::test_the_metrics_name_the_age_of_the_last_state_and_the_failures`
    - `tests/unit/features/test_context_registrations.py::test_basis_says_it_is_the_perpetuals_mark_against_the_venues_index`
    - `tests/unit/features/test_context_registrations.py::test_funding_z_says_it_reads_settled_history_only`
    - `tests/unit/features/test_context_registrations.py::test_open_interest_says_it_is_the_venues_usd_figure_of_the_venues_perpetual`
    - `tests/unit/pipeline/test_context_main.py::test_a_bad_port_is_refused[-1]`
    - `tests/unit/pipeline/test_context_main.py::test_a_bad_port_is_refused[0]`
    - `tests/unit/pipeline/test_context_main.py::test_a_bad_port_is_refused[70000]`
    - `tests/unit/pipeline/test_context_main.py::test_a_bad_port_is_refused[abc]`
    - `tests/unit/pipeline/test_context_main.py::test_a_venue_is_required`
    - `tests/unit/pipeline/test_context_main.py::test_an_unknown_venue_is_refused_naming_the_known_ones`
    - `tests/unit/pipeline/test_context_main.py::test_symbols_and_port_can_be_set_and_are_trimmed`
    - `tests/unit/pipeline/test_context_main.py::test_the_symbols_default_to_the_ones_the_deployment_shows[binance-symbols0]`
    - `tests/unit/pipeline/test_context_main.py::test_the_symbols_default_to_the_ones_the_deployment_shows[bybit-symbols1]`
    - `tests/unit/pipeline/test_context_main.py::test_the_symbols_default_to_the_ones_the_deployment_shows[okx-symbols2]`
    - `tests/unit/pipeline/test_context_pass.py::test_a_constant_funding_series_writes_no_funding_z_not_zero`
    - `tests/unit/pipeline/test_context_pass.py::test_a_failing_series_is_reported_and_does_not_stop_the_others`
    - `tests/unit/pipeline/test_context_pass.py::test_a_later_pass_writes_only_the_new_bars`
    - `tests/unit/pipeline/test_context_pass.py::test_a_poll_older_than_the_bound_writes_no_open_interest_and_no_basis`
    - `tests/unit/pipeline/test_context_pass.py::test_a_second_pass_over_the_same_bars_writes_nothing`
    - `tests/unit/pipeline/test_context_pass.py::test_a_series_that_is_not_given_a_perpetual_is_ignored_even_if_states_exist_under_its_name`
    - `tests/unit/pipeline/test_context_pass.py::test_a_series_with_no_perpetual_or_no_states_gets_nothing`
    - `tests/unit/pipeline/test_context_pass.py::test_a_settled_rate_is_available_from_its_settlement_not_from_when_it_was_loaded`
    - `tests/unit/pipeline/test_context_pass.py::test_a_settlement_older_than_one_interval_plus_the_margin_is_stale`
    - `tests/unit/pipeline/test_context_pass.py::test_a_spot_series_is_given_its_venues_perpetual_and_unknown_series_are_given_nothing`
    - `tests/unit/pipeline/test_context_pass.py::test_a_state_dated_after_the_close_is_not_used_when_the_venue_clock_runs_ahead`
    - `tests/unit/pipeline/test_context_pass.py::test_a_state_observed_after_the_close_is_not_used_even_if_its_event_time_is_earlier`
    - `tests/unit/pipeline/test_context_pass.py::test_a_state_without_the_field_leaves_that_feature_absent`
    - `tests/unit/pipeline/test_context_pass.py::test_appending_later_rows_changes_nothing_at_an_earlier_close`
    - `tests/unit/pipeline/test_context_pass.py::test_bars_before_any_observation_get_nothing_not_zeros`
    - `tests/unit/pipeline/test_context_pass.py::test_basis_also_uses_only_what_had_been_received_by_the_close`
    - `tests/unit/pipeline/test_context_pass.py::test_binance_open_interest_has_its_own_longer_bound`
    - `tests/unit/pipeline/test_context_pass.py::test_every_timeframe_gets_its_value_as_of_its_own_close`
    - `tests/unit/pipeline/test_context_pass.py::test_fewer_than_24_settlements_writes_no_funding_z`
    - `tests/unit/pipeline/test_context_pass.py::test_funding_z_exists_for_the_whole_interval_not_for_five_minutes_of_it`
    - `tests/unit/pipeline/test_context_pass.py::test_no_states_at_all_is_no_values`
    - `tests/unit/pipeline/test_context_pass.py::test_polled_funding_estimates_never_enter_the_funding_z`
    - `tests/unit/pipeline/test_context_pass.py::test_the_pass_does_not_touch_the_flow_features`
    - `tests/unit/pipeline/test_context_pass.py::test_the_pass_skips_bars_that_are_not_final`
    - `tests/unit/pipeline/test_context_pass.py::test_the_pass_writes_the_three_features_at_every_final_bars_close`
    - `tests/unit/pipeline/test_context_pass.py::test_the_three_values_at_a_close_are_what_the_library_gives_at_that_instant`
    - `tests/unit/pipeline/test_context_pass.py::test_values_are_plain_finite_floats`
    - `tests/unit/tables/test_derivatives_state.py::test_a_new_sink_knows_what_an_earlier_one_stored`
    - `tests/unit/tables/test_derivatives_state.py::test_an_absent_field_stays_absent_and_is_never_a_default`
    - `tests/unit/tables/test_derivatives_state.py::test_identity_is_venue_symbol_time_and_source`
    - `tests/unit/tables/test_derivatives_state.py::test_prices_are_decimal_and_a_row_round_trips_exactly`
    - `tests/unit/tables/test_derivatives_state.py::test_states_are_read_back_grouped_by_market_and_sorted_by_event_time`
    - `tests/unit/tables/test_derivatives_state.py::test_the_schema_is_section_10_4_plus_the_source_and_both_times`
    - `tests/unit/tables/test_derivatives_state.py::test_the_sink_stores_a_state_once_however_often_it_is_offered`
- **Outcomes:** [[OUT-2026-10-11-implement-derivatives-collector]], [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

The collector is shared infrastructure for [[REQ-WP-094]] and [[REQ-WP-095]]: one process per venue, one set of
connection, shutdown and health code. [[ADR-070]] records why it is a separate service and why the feature pass
lives in the worker (one writer to `feature_snapshots`).
