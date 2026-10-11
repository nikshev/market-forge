---
id: REQ-WP-099
title: "The two DEX panes have a source: HyperEVM's WHYPE/USDC pools are collected, and the HYPE series carry swap imbalance and active liquidity"
type: work-package
prd_ref: "§18.11.2, §18A.4, §19, §27.3; owner's direction 2026-10-11"
prd_lines: "4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-098, REQ-WP-097, REQ-WP-059, REQ-WP-063, REQ-WP-058, REQ-WP-053, REQ-WP-060]
tags: [dex, hyperevm, panes, collector, defi]
hard_gated: false
---

## Requirement

After [[REQ-WP-097]] every lower pane had a producer except the two DEX ones, and `make panes-report` says why:
**"no DEX source: this deployment runs no DEX ingest"**. The decoders ([[REQ-WP-058]]), the tables
([[REQ-WP-053]], [[REQ-WP-060]]) and the two features ([[REQ-WP-059]], [[REQ-WP-063]]) all exist; nothing reads the chain.
On 2026-10-11 the owner chose to build the source.

1. **A DEX collector.** One more service, public HyperEVM JSON-RPC only (no key), that every minute reads the logs of the
   two busiest WHYPE/USDC pools on chain 999 (a Uniswap v3 pool and an Algebra Integral pool, pinned from
   [[REQ-WP-058]]'s measurement) from where it last stopped, and stores each `Swap` in `dex_swaps`; and reads each pool's
   `liquidity()` and stores it in `dex_state`. The protocol comes from the pinned registry, never from the event.
2. **A series to carry them.** The DEX features are keyed by `(venue, symbol)` ([[REQ-WP-059]]), and HyperEVM has no
   bars: the pools price HYPE, so they are shown on a HYPE market. Bybit's `HYPEUSDT` perpetual is ingested (a new
   ingest service) and collected like `BTCUSDT`, and is a series the DEX panes are read from. **OKX's `HYPE-USDT-SWAP`
   is ingested beside it**, carries them too, and makes the HYPE series' venue-basis pane a two-venue consensus (the first deployed run found
   a pane with no producer: a market in no consensus group has no consensus to read, and says so with a 404).
3. **The features at each bar's close.** The worker computes `dex_swap_imbalance` (a trailing five-minute window, both
   pools) and `dex_active_liquidity` (the busiest pool's most recent reading) for the HYPE series at every final bar's
   close, as of that close: an event counts only if its block time **and** the time we stored it are at or before the close.

## Acceptance

- A recorded `eth_getLogs` answer from HyperEVM becomes `DexSwapEvent`s whose amounts, price, tick and liquidity equal the
  decoder's (REQ-WP-058) and whose event time is the block's, with no further request for the block.
- A pool the registry does not name is refused, not decoded as the family it resembles; a pool-level fee is never invented
  for an Algebra swap.
- A poll that fails, is rate limited or is refused by the node stores **nothing and does not move the cursor**; the next
  poll asks for the same range. A range wider than the node allows is asked for in pieces.
- A stored swap is never stored twice (restart, or an overlapping range).
- `dex_swap_imbalance` at a close counts swaps strictly at or before the close that had been stored by it; a window in
  which the collector did not poll for every minute yields **no** value, not zero; a window with no swap yields none.
- `dex_active_liquidity` at a close is the most recent reading at or before it, and none if that reading is older than
  three polls.
- `make panes-report` shows `data` for the HYPE series in both DEX panes at 1m and in Venue basis (both HYPE venues);
  the other series read "no DEX pool is registered for this asset" (not "no DEX ingest").
- The new ingest and collector services are started without recreating any running container.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-151-dex-panes]]
- **Tests:**
    - `tests/tools/panes/test_classify.py::test_a_dex_pane_that_has_data_is_data_whatever_the_market_says`
    - `tests/tools/panes/test_classify.py::test_a_market_with_no_registered_pool_says_so_and_does_not_blame_the_collector`
    - `tests/tools/panes/test_classify.py::test_a_pool_market_with_liquidity_but_no_imbalance_is_a_quiet_window_the_collector_saw`
    - `tests/tools/panes/test_classify.py::test_a_pool_market_with_no_reading_at_all_is_no_producer`
    - `tests/tools/panes/test_classify.py::test_only_the_market_the_pools_price_is_gathered_as_having_a_dex_pool`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_a_call_posts_a_json_rpc_request_and_returns_the_result`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_a_range_wider_than_the_node_allows_is_refused_before_it_is_sent`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_a_rate_limit_inside_a_200_answer_is_a_rate_limit`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_a_reading_the_node_cut_short_is_a_failure_not_a_zero`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_a_transport_error_is_an_rpc_failure`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_a_uniswap_v3_pool_is_read_through_slot0_and_its_liquidity`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_an_algebra_pool_is_read_through_global_state_and_its_fee_is_the_published_one`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_every_other_failure_is_an_rpc_failure_that_is_not_a_rate_limit[error-object]`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_every_other_failure_is_an_rpc_failure_that_is_not_a_rate_limit[http-500]`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_every_other_failure_is_an_rpc_failure_that_is_not_a_rate_limit[http-503-with-a-result]`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_every_other_failure_is_an_rpc_failure_that_is_not_a_rate_limit[no-result]`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_every_other_failure_is_an_rpc_failure_that_is_not_a_rate_limit[not-json]`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_http_429_is_a_rate_limit_and_honours_retry_after`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_logs_ask_for_both_pools_and_the_swap_topic_over_an_inclusive_range`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_the_head_is_the_hex_block_number_as_an_int`
    - `tests/unit/connectors/hyperevm/test_rpc.py::test_the_widest_allowed_range_is_one_thousand_blocks_inclusive`
    - `tests/unit/context/test_sources_series.py::test_hype_is_a_perpetual_on_two_venues_so_its_venue_basis_has_a_consensus`
    - `tests/unit/context/test_sources_series.py::test_the_series_the_dex_pools_are_shown_on_is_an_ingested_perpetual_with_derivatives`
    - `tests/unit/crossvenue/test_consensus_write.py::test_the_hype_perpetual_group_has_two_venues_so_its_pane_has_a_consensus`
    - `tests/unit/deploy/test_compose_logging.py::test_the_dex_collector_is_a_service_that_reports_its_own_health_and_holds_no_key`
    - `tests/unit/deploy/test_compose_logging.py::test_the_hype_ingest_service_reads_the_hype_symbol_from_bybit`
    - `tests/unit/deploy/test_compose_logging.py::test_the_okx_hype_ingest_reads_the_hype_swap_from_okx`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_catch_up_is_spread_over_polls_not_hammered_into_one`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_failed_head_request_is_a_failed_poll`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_failed_logs_request_stores_nothing_and_leaves_the_cursor[failure0]`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_failed_logs_request_stores_nothing_and_leaves_the_cursor[failure1]`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_failed_poll_is_not_a_success_and_a_good_one_is`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_gap_wider_than_the_node_allows_is_asked_in_contiguous_pieces`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_log_from_a_pool_the_registry_does_not_name_is_refused`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_log_that_cannot_be_read_is_counted_and_the_rest_of_the_piece_is_kept`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_log_that_is_not_a_swap_is_refused`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_log_the_node_returns_from_a_block_already_stored_is_dropped`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_log_without_a_block_time_is_refused_not_dated_by_our_clock`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_piece_that_fails_leaves_the_cursor_where_the_last_good_piece_ended`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_poll_stores_every_swap_up_to_the_safe_head_and_moves_the_cursor_there`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_poll_that_is_not_due_asks_nothing`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_poll_with_no_new_block_still_confirms_the_collector_is_listening`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_rate_limit_waits_at_least_as_long_as_the_node_asked`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_reading_carries_the_liquidity_the_pool_reported`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_reading_that_fails_is_not_stored_and_the_swaps_still_are`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_removed_log_is_refused`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_restart_from_the_last_stored_block_does_not_store_a_swap_twice`
    - `tests/unit/dex/test_hyperevm_collect.py::test_a_swap_is_stored_with_the_time_of_the_poll_as_its_ingest_time`
    - `tests/unit/dex/test_hyperevm_collect.py::test_blocks_already_stored_are_never_asked_for_again`
    - `tests/unit/dex/test_hyperevm_collect.py::test_buffers_are_committed_on_the_interval_and_a_failed_commit_keeps_its_rows`
    - `tests/unit/dex/test_hyperevm_collect.py::test_each_caught_up_poll_stores_one_reading_per_pool_dated_at_the_poll`
    - `tests/unit/dex/test_hyperevm_collect.py::test_each_swap_names_the_protocol_of_the_pool_that_emitted_it`
    - `tests/unit/dex/test_hyperevm_collect.py::test_every_recorded_log_becomes_a_swap_whose_numbers_are_the_logs_own`
    - `tests/unit/dex/test_hyperevm_collect.py::test_no_reading_is_stored_while_the_swaps_are_not_caught_up`
    - `tests/unit/dex/test_hyperevm_collect.py::test_one_pool_failing_stores_no_reading_for_either`
    - `tests/unit/dex/test_hyperevm_collect.py::test_the_event_time_is_the_blocks_and_the_ingest_time_is_when_we_stored_it`
    - `tests/unit/dex/test_hyperevm_collect.py::test_the_first_poll_with_no_history_starts_a_fixed_distance_behind_the_safe_head`
    - `tests/unit/dex/test_hyperevm_collect.py::test_the_head_block_itself_is_never_asked_for`
    - `tests/unit/dex/test_hyperevm_collect.py::test_the_next_poll_after_a_failure_asks_for_the_same_blocks`
    - `tests/unit/dex/test_hyperevm_collect.py::test_the_price_is_usdc_per_whype_from_the_square_root_price`
    - `tests/unit/dex/test_hyperevm_pools.py::test_addresses_are_lowercase_so_a_log_can_be_matched_by_equality`
    - `tests/unit/dex/test_hyperevm_pools.py::test_an_algebra_pool_carries_no_pool_level_fee_and_a_v3_pool_does`
    - `tests/unit/dex/test_hyperevm_pools.py::test_every_pool_comes_from_a_factory_the_decoders_know`
    - `tests/unit/dex/test_hyperevm_pools.py::test_the_liquidity_pool_is_one_of_the_registered_pools`
    - `tests/unit/dex/test_hyperevm_pools.py::test_the_registry_names_a_uniswap_v3_pool_and_an_algebra_pool`
    - `tests/unit/dex/test_hyperevm_pools.py::test_the_series_the_pools_are_shown_on_is_one_the_deployment_ingests`
    - `tests/unit/dex/test_hyperevm_pools.py::test_the_two_pools_are_the_same_pair_in_the_same_order`
    - `tests/unit/dex/test_hyperevm_pools.py::test_token_decimals_are_known_for_both_tokens`
    - `tests/unit/features/test_dex_values.py::test_a_pool_nobody_read_leaves_the_window_uncovered`
    - `tests/unit/features/test_dex_values.py::test_a_reading_exactly_three_polls_old_still_counts`
    - `tests/unit/features/test_dex_values.py::test_a_reading_of_a_grade_that_cannot_carry_liquidity_is_ignored`
    - `tests/unit/features/test_dex_values.py::test_a_reading_older_than_three_polls_is_not_the_liquidity_now`
    - `tests/unit/features/test_dex_values.py::test_a_swap_dated_after_the_close_is_not_in_it_even_if_stored_early`
    - `tests/unit/features/test_dex_values.py::test_a_swap_stored_after_the_close_is_not_in_that_closes_value`
    - `tests/unit/features/test_dex_values.py::test_a_window_the_collector_did_not_cover_has_no_imbalance_even_with_swaps_in_it`
    - `tests/unit/features/test_dex_values.py::test_a_window_with_no_swap_has_no_imbalance_not_zero`
    - `tests/unit/features/test_dex_values.py::test_liquidity_does_not_need_a_covered_window`
    - `tests/unit/features/test_dex_values.py::test_the_active_liquidity_is_the_liquidity_pools_latest_reading_at_or_before_the_close`
    - `tests/unit/features/test_dex_values.py::test_the_features_are_the_two_the_registry_names`
    - `tests/unit/features/test_dex_values.py::test_the_imbalance_is_net_flow_over_gross_flow_across_both_pools`
    - `tests/unit/features/test_dex_values.py::test_the_imbalance_never_reads_a_reading_from_after_the_close_as_coverage`
    - `tests/unit/features/test_dex_values.py::test_the_other_pools_liquidity_is_not_the_one_shown`
    - `tests/unit/features/test_dex_values.py::test_the_window_is_five_minutes_and_staleness_is_three_polls`
    - `tests/unit/features/test_dex_values.py::test_the_window_is_open_at_its_floor_and_closed_at_the_close`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_bar_the_collector_did_not_cover_gets_no_imbalance`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_covered_bar_with_no_swap_has_liquidity_and_no_imbalance`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_pass_with_no_dex_tables_content_writes_nothing_for_them`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_second_pass_writes_nothing_more`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_series_without_pools_gets_no_dex_feature`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_swap_of_another_chain_is_not_one_of_the_pools`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_a_swap_stored_after_the_close_is_not_in_the_bar`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_every_market_the_pools_price_gets_the_features`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_the_pass_writes_both_features_at_a_covered_close`
    - `tests/unit/pipeline/test_context_pass_dex.py::test_the_value_at_a_close_does_not_change_when_later_swaps_arrive`
    - `tests/unit/pipeline/test_dex_main.py::test_a_bad_port_is_refused[-1]`
    - `tests/unit/pipeline/test_dex_main.py::test_a_bad_port_is_refused[0]`
    - `tests/unit/pipeline/test_dex_main.py::test_a_bad_port_is_refused[70000]`
    - `tests/unit/pipeline/test_dex_main.py::test_a_bad_port_is_refused[abc]`
    - `tests/unit/pipeline/test_dex_main.py::test_a_node_that_is_not_an_http_url_is_refused[ftp://rpc.example]`
    - `tests/unit/pipeline/test_dex_main.py::test_a_node_that_is_not_an_http_url_is_refused[javascript:1]`
    - `tests/unit/pipeline/test_dex_main.py::test_a_node_that_is_not_an_http_url_is_refused[rpc.example]`
    - `tests/unit/pipeline/test_dex_main.py::test_an_empty_table_has_no_last_block`
    - `tests/unit/pipeline/test_dex_main.py::test_the_collector_resumes_from_the_last_block_it_stored`
    - `tests/unit/pipeline/test_dex_main.py::test_the_defaults_are_the_public_node_and_the_collectors_port`
    - `tests/unit/pipeline/test_dex_main.py::test_the_node_and_the_port_can_be_set_and_are_trimmed`
    - `tests/unit/tables/test_dex_tables.py::test_a_pool_reading_is_a_partial_ticks_state_that_the_liquidity_feature_accepts`
    - `tests/unit/tables/test_dex_tables.py::test_a_swap_keeps_the_time_it_was_stored_apart_from_the_time_it_happened`
- **Code:**
    - `src/channelflow/chain/hyperevm.py`
    - `src/channelflow/connectors/hyperevm/__init__.py`
    - `src/channelflow/connectors/hyperevm/rpc.py`
    - `src/channelflow/context/sources.py`
    - `src/channelflow/dex/hyperevm_collect.py`
    - `src/channelflow/dex/hyperevm_pools.py`
    - `src/channelflow/features/dex.py`
    - `src/channelflow/features/dex_values.py`
    - `src/channelflow/pipeline/context_pass.py`
    - `src/channelflow/pipeline/dex_main.py`
    - `src/channelflow/tables/dex_state.py`
    - `src/channelflow/tables/dex_swaps.py`
    - `tools/panes/classify.py`
- **Outcomes:** [[OUT-2026-10-11-implement-dex-panes]], [[OUT-2026-10-11-spec-dex-panes]]
<!-- trace:end -->
