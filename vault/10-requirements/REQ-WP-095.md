---
id: REQ-WP-095
title: "The order-flow panes (OFI, depth imbalance) and the venues' quotes are fed by a top-of-book subscription"
type: work-package
prd_ref: "§10.3, §15.1, §15.3, §17.1, §27.3; owner's direction 2026-10-11"
prd_lines: "891-902, 2338-2385, 4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-093, REQ-WP-027, REQ-WP-084]
tags: [order-book, ofi, depth, quotes, collector, panes]
hard_gated: false
---

## Requirement

`OFI (1m)` and `Depth imbalance (10)` read "no data", and so does the cross-venue consensus
([[REQ-WP-091]]) whose own requirement says "no venue's mid is available at all". The cause is one thing: **the
ingest subscribes to trades only**, so there is no order book anywhere in the system. The consumers exist
(`features/ofi.py`'s `OFITracker`, `features/instant.py`'s `depth_imbalance_levels`, `book/service.py`'s
`BookService`, `tables/quotes.py`) and have no feed.

This requirement adds, to the collector of [[REQ-WP-093]]:

1. **A book subscription per venue**, public and keyless, probed from this host on 2026-10-11:
   Binance partial depth `<symbol>@depth<N>@<interval>`, Bybit `orderbook.<N>.<symbol>`, OKX `books5`/`books`.
   **Snapshot-style streams are used on purpose** where the venue offers them: each frame is the whole top of the
   book, so there is no delta stream to reconstruct and no sequence gap to recover from (§11.1's local book
   reconstruction is not needed to read the top ten levels). A frame is normalised into the project's
   `BookSnapshot`.
2. **Per-minute book summaries, computed in event time.** For each symbol the collector feeds the existing
   `OFITracker` and `BookService` and, when the first frame of the next minute arrives, finalises the minute that
   just ended using only frames with `event_time` before the boundary: the 1-minute OFI (§15.3's window), the
   depth imbalance over the top 10 levels (§15.1's `DI_10`), the top-of-book quote (bid, ask, mid) as of the
   boundary, and **how many frames the minute rested on**. They are stored in an append-only table; the quote
   also in the existing `quotes` table, which is what the consensus reads.
3. **The worker writes `ofi_1m` and `depth_imbalance_10` per bar**, as of the bar's close, from the minute
   summary that closed at or before it, for every timeframe.

Rules that hold:

- **No look-ahead**: a minute is finalised from frames before its closing boundary; the worker reads summaries
  with `close <= bar close`.
- **A thin minute is not a balanced one.** `OFIWindow` already carries its observation count because "zero flow
  and no data both read as 0". A minute with no frames (a reconnect) is stored with a count of zero and the
  worker writes **nothing** for it.
- **The sampling rate is a stated limit, not a hidden one.** The streams are snapshots at 100-1000 ms, so the OFI
  here is top-of-book OFI computed from sampled snapshots, not from every book event. It is a real measurement
  of what the sampled book did and not the exchange's full event-level OFI; the feature's registration says so.
- **Two market types, not one book**: Binance's series is a spot market and the book subscribed to is its spot
  book (the same stream host the trade ingest uses); Bybit's and OKX's are perpetuals and their books are the
  perpetual's. No book is attributed to a market it is not.

## Acceptance

- For a recorded frame of each venue the normaliser yields the expected `BookSnapshot` (best bid below best ask,
  levels ordered, quantities positive); a crossed or empty book is refused with a reason, never stored.
- For a scripted frame sequence across a minute boundary the stored minute carries the OFI, the depth imbalance
  and the mid a hand calculation gives; the frames after the boundary do not change it (a test).
- A reconnect produces a minute with a zero count and no feature rows for it.
- The writer's `ofi_1m` and `depth_imbalance_10` at a bar's close equal the stored summary of the last minute
  closed at or before it, and are unchanged when later summaries are appended (a test).
- `quotes` rows exist for each subscribed market at each minute close, with exchange time and receive time apart.
- On the running stack the two panes are enabled for the Binance, Bybit and OKX BTC series and the recorded
  query shows values inside their bounds ([-1, 1] for the imbalance).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-147-book-subscription]]
- **Tests:**
    - `tests/unit/book/test_sequence.py::test_a_delta_that_names_no_predecessor_is_still_judged_by_consecutive_ids`
    - `tests/unit/book/test_sequence.py::test_a_named_predecessor_that_is_what_was_applied_is_continuous_whatever_the_ids`
    - `tests/unit/book/test_sequence.py::test_a_named_predecessor_that_was_not_applied_is_a_gap_even_if_the_ids_are_consecutive`
    - `tests/unit/context/test_book_stream.py::test_a_bybit_sequence_gap_closes_the_connection_so_a_fresh_snapshot_is_fetched`
    - `tests/unit/context/test_book_stream.py::test_a_frame_for_a_symbol_not_watched_is_ignored_even_across_a_minute_boundary`
    - `tests/unit/context/test_book_stream.py::test_a_frame_that_is_not_json_is_counted_and_the_stream_goes_on`
    - `tests/unit/context/test_book_stream.py::test_a_minute_of_frames_becomes_one_stored_minute_and_a_quote`
    - `tests/unit/context/test_book_stream.py::test_a_reconnect_resets_every_book_so_no_flow_spans_the_gap`
    - `tests/unit/context/test_book_stream.py::test_a_recorded_binance_frame_is_a_ten_level_snapshot_of_the_symbol_in_its_stream_name`
    - `tests/unit/context/test_book_stream.py::test_a_silent_minute_is_stored_with_a_zero_count_by_the_clock`
    - `tests/unit/context/test_book_stream.py::test_an_unknown_venue_has_no_book_stream`
    - `tests/unit/context/test_book_stream.py::test_binance_is_the_spot_partial_depth_stream_of_each_symbol_on_the_combined_endpoint`
    - `tests/unit/context/test_book_stream.py::test_bybit_acknowledgements_are_not_book_messages`
    - `tests/unit/context/test_book_stream.py::test_bybit_asks_for_every_symbol_watched`
    - `tests/unit/context/test_book_stream.py::test_bybit_is_the_linear_fifty_level_book_one_topic_per_symbol`
    - `tests/unit/context/test_book_stream.py::test_each_venues_book_is_of_the_market_its_series_is`
    - `tests/unit/context/test_book_stream.py::test_okx_acks_and_other_channels_are_not_book_messages`
    - `tests/unit/context/test_book_stream.py::test_okx_is_the_books_channel_which_has_ten_levels_not_books5_which_has_five`
    - `tests/unit/context/test_book_stream.py::test_okx_without_a_contract_value_refuses_rather_than_reading_contracts_as_base_units`
    - `tests/unit/context/test_book_stream.py::test_okxs_bare_pong_is_not_a_failed_frame`
    - `tests/unit/context/test_book_stream.py::test_recorded_bybit_frames_are_a_snapshot_then_deltas_with_a_continuous_sequence`
    - `tests/unit/context/test_book_stream.py::test_recorded_okx_frames_become_a_snapshot_then_updates_with_sizes_in_base_units`
    - `tests/unit/context/test_book_stream.py::test_the_recorded_okx_frames_are_one_continuous_chain_and_never_ask_for_a_resync`
    - `tests/unit/context/test_minute_book.py::test_a_book_with_fewer_than_ten_levels_a_side_has_no_ten_level_imbalance`
    - `tests/unit/context/test_minute_book.py::test_a_crossed_book_is_refused_and_does_not_become_a_quote`
    - `tests/unit/context/test_minute_book.py::test_a_minute_is_finalised_by_the_first_message_of_the_next_one`
    - `tests/unit/context/test_minute_book.py::test_a_minute_with_no_frame_at_all_has_a_count_of_zero_and_nothing_else`
    - `tests/unit/context/test_minute_book.py::test_a_reset_breaks_the_ofi_baseline_so_no_increment_spans_the_gap`
    - `tests/unit/context/test_minute_book.py::test_a_resync_snapshot_clears_the_request`
    - `tests/unit/context/test_minute_book.py::test_a_sequence_gap_asks_for_a_resync_and_breaks_the_baseline`
    - `tests/unit/context/test_minute_book.py::test_a_silent_minute_is_finalised_by_the_clock_with_a_zero_count_and_no_values`
    - `tests/unit/context/test_minute_book.py::test_depth_imbalance_is_the_hand_computed_ten_level_ratio`
    - `tests/unit/context/test_minute_book.py::test_each_minutes_ofi_is_its_own_and_not_a_running_total`
    - `tests/unit/context/test_minute_book.py::test_ofi_over_the_minute_is_the_sum_of_the_second_by_second_increments`
    - `tests/unit/context/test_minute_book.py::test_the_summary_is_the_book_before_the_message_that_closed_the_minute`
    - `tests/unit/context/test_minute_book.py::test_the_tick_does_nothing_before_the_minute_has_ended`
    - `tests/unit/context/test_streams.py::test_the_reconnect_callback_runs_once_for_each_new_connection_and_not_for_the_first`
    - `tests/unit/context/test_streams.py::test_the_tick_callback_runs_on_every_step_with_the_time_so_silent_minutes_can_close`
    - `tests/unit/features/test_book_values.py::test_a_book_without_ten_levels_has_no_depth_imbalance_but_keeps_its_ofi`
    - `tests/unit/features/test_book_values.py::test_a_minute_older_than_two_minutes_at_the_close_is_stale`
    - `tests/unit/features/test_book_values.py::test_a_minute_that_ends_after_the_close_is_not_used`
    - `tests/unit/features/test_book_values.py::test_a_minute_with_no_frame_writes_nothing`
    - `tests/unit/features/test_book_values.py::test_an_ofi_of_exactly_zero_is_a_reading_when_there_were_observations`
    - `tests/unit/features/test_book_values.py::test_appending_later_minutes_changes_nothing_at_an_earlier_close`
    - `tests/unit/features/test_book_values.py::test_no_minutes_is_no_values`
    - `tests/unit/features/test_book_values.py::test_the_precomputed_times_give_the_same_answer`
    - `tests/unit/features/test_book_values.py::test_the_value_at_a_close_is_the_latest_minute_that_ended_at_or_before_it`
    - `tests/unit/features/test_book_values.py::test_too_few_observations_means_no_ofi_but_the_depth_imbalance_can_still_stand`
    - `tests/unit/features/test_context_registrations.py::test_ofi_says_it_is_sampled_once_a_second_and_not_the_exchanges_event_level_figure`
    - `tests/unit/features/test_context_registrations.py::test_the_ten_level_imbalance_says_a_shallower_book_gets_no_number`
    - `tests/unit/pipeline/test_context_main.py::test_the_book_stream_can_be_chosen_alone`
    - `tests/unit/pipeline/test_context_pass_book.py::test_a_bar_with_no_book_minute_gets_no_book_feature`
    - `tests/unit/pipeline/test_context_pass_book.py::test_a_second_pass_writes_nothing_more`
    - `tests/unit/pipeline/test_context_pass_book.py::test_a_series_is_given_its_own_markets_book_not_a_perpetuals`
    - `tests/unit/pipeline/test_context_pass_book.py::test_a_zero_count_minute_writes_nothing`
    - `tests/unit/pipeline/test_context_pass_book.py::test_all_three_families_are_one_commit`
    - `tests/unit/pipeline/test_context_pass_book.py::test_one_series_failing_in_the_book_step_is_reported_and_the_others_go_on`
    - `tests/unit/pipeline/test_context_pass_book.py::test_the_pass_writes_ofi_and_depth_imbalance_at_a_bars_close`
    - `tests/unit/pipeline/test_context_pass_book.py::test_the_value_is_the_minute_that_ended_at_or_before_the_close_and_no_later_one`
    - `tests/unit/tables/test_book_minutes.py::test_a_flush_with_nothing_pending_commits_nothing`
    - `tests/unit/tables/test_book_minutes.py::test_a_minute_with_a_quote_also_writes_the_quote_with_the_two_times_apart`
    - `tests/unit/tables/test_book_minutes.py::test_a_minute_without_a_top_of_book_writes_no_quote`
    - `tests/unit/tables/test_book_minutes.py::test_a_row_carries_the_minute_the_receipt_and_decimals_exactly`
    - `tests/unit/tables/test_book_minutes.py::test_a_row_round_trips_and_an_absent_value_stays_absent`
    - `tests/unit/tables/test_book_minutes.py::test_an_empty_minute_is_stored_as_a_count_of_zero_and_writes_no_quote`
    - `tests/unit/tables/test_book_minutes.py::test_minutes_are_read_back_by_market_oldest_first`
    - `tests/unit/tables/test_book_minutes.py::test_minutes_that_differ_in_venue_symbol_or_time_are_different_minutes[different0]`
    - `tests/unit/tables/test_book_minutes.py::test_minutes_that_differ_in_venue_symbol_or_time_are_different_minutes[different1]`
    - `tests/unit/tables/test_book_minutes.py::test_minutes_that_differ_in_venue_symbol_or_time_are_different_minutes[different2]`
    - `tests/unit/tables/test_book_minutes.py::test_the_schema_has_the_minute_its_two_times_and_what_it_amounted_to`
    - `tests/unit/tables/test_book_minutes.py::test_the_sink_stores_a_minute_and_its_quote_once`
- **Code:**
    - `src/channelflow/context/book.py`
    - `src/channelflow/context/minute_book.py`
    - `src/channelflow/context/streams.py`
    - `src/channelflow/features/book_values.py`
    - `src/channelflow/tables/book_minutes.py`
- **Outcomes:** [[OUT-2026-10-11-implement-book-subscription]], [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

Host load is a constraint, not an afterthought: five books at 100 ms in Python on a machine that also runs the
live stack and other projects. The plan measures the collector's CPU before and after, and chooses the
interval that the host can carry. A slower stream is an honest trade; a starved MinIO is not
([[REQ-INFRA-012]]).
