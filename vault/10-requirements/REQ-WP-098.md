---
id: REQ-WP-098
title: "The Binance spot series get a consensus: OKX spot is ingested, its books are collected, and both spot groups have two venues"
type: work-package
prd_ref: "§17.1, §17.3, §27.3; owner's direction 2026-10-11"
prd_lines: "2520-2552, 4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-096, REQ-WP-095, REQ-WP-093, REQ-WP-076]
tags: [consensus, venue-basis, okx, spot, ingest]
hard_gated: false
---

## Requirement

[[REQ-WP-096]] wrote the consensus and left one thing true and visible: **the three Binance spot series have a venue
basis pane that reads "absent: only 1 venue(s) could contribute"**, because no other spot venue is ingested. On
2026-10-11 the owner, shown that, chose to add a second one.

OKX lists spot `BTC-USDT`, `ETH-USDT` and `SOL-USDT`, the same three pairs Binance's series are. This requirement
ingests them and carries them through the whole path, so that each spot asset has **two venues** and a consensus:

1. **Trades -> bars.** One ingest process per symbol, exactly as the existing ones (`ingest_main`, one symbol each):
   `okx` `BTC-USDT`, `ETH-USDT`, `SOL-USDT`. `okx_market_type` already answers `spot` for a `BASE-QUOTE` instrument.
   The markets are registered, bars are built and resampled, and the worker's existing passes (flow features,
   channels, signals) cover them like any other series.
2. **Their books.** The collector of OKX also subscribes to the `books` channel of the three spot instruments.
   **A spot size is in base units already**: the contract value that converts OKX's *swap* contracts must not be
   applied to it (a spot book scaled by a swap's `ctVal` would be wrong by a factor of 100 or more), so the
   conversion is decided by the instrument's kind, and a swap without a contract value is still refused.
3. **Their derivatives.** A spot series is shown its venue's perpetual of the same pair for open interest, funding and
   basis ([[REQ-WP-093]]): OKX's spot series are mapped to `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, so the
   OKX collector also polls and listens to the two perpetuals it did not before.
4. **The consensus.** The three spot groups (BTC, ETH, SOL) are now Binance + OKX; the consensus is stored under both
   symbols a group's members use (`BTCUSDT` and `BTC-USDT`, ...).

## Acceptance

- The deployment ingests OKX spot `BTC-USDT`, `ETH-USDT` and `SOL-USDT`: the `markets` read lists them as `spot`, bars
  accumulate, and the resampler builds every configured timeframe for them.
- A recorded OKX spot `books` frame is turned into a `BookSnapshot` whose sizes are the frame's sizes **unscaled**; the
  same frame shape for a swap is scaled by that swap's contract value, and a swap with none is refused (tests).
- The OKX book summaries and quotes exist for the three spot symbols and the perpetual; the spot minutes are labelled
  `spot` and the swap's `perp`.
- `consensus` rows exist for each spot group with `venue_count` 2, a price, and no refusal; the venue-basis read for
  Binance and OKX spot series returns points equal to `10000 * (mid / consensus - 1)` over the stored mids (a recorded
  query).
- `make panes-report`: the six spot series (Binance and OKX x BTC/ETH/SOL) have `data` in the Venue basis pane at 1m.
- Existing containers are not recreated by the new ingest services' start; the worker is rebuilt last.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-150-second-spot-venue]]
- **Tests:**
    - `tests/unit/context/test_book_stream.py::test_a_recorded_okx_spot_frame_keeps_its_sizes_because_they_are_already_base_units`
    - `tests/unit/context/test_book_stream.py::test_a_spot_instrument_is_not_scaled_even_if_a_contract_value_is_offered_for_it`
    - `tests/unit/context/test_book_stream.py::test_each_minute_is_stored_with_its_own_instruments_market_type`
    - `tests/unit/context/test_book_stream.py::test_okx_asks_for_every_book_symbol_in_one_subscription`
    - `tests/unit/context/test_book_stream.py::test_the_market_type_of_a_book_is_asked_by_instrument_not_by_venue`
    - `tests/unit/context/test_book_stream.py::test_the_same_frame_shape_for_a_swap_is_scaled_and_labelled_perp`
    - `tests/unit/context/test_sources_series.py::test_each_okx_spot_series_is_shown_the_perpetual_of_its_own_pair`
    - `tests/unit/context/test_sources_series.py::test_every_series_has_a_perpetual_and_that_perpetual_is_one_the_venue_polls`
    - `tests/unit/context/test_sources_series.py::test_the_book_symbols_of_a_venue_are_its_own_series_not_its_perpetuals`
    - `tests/unit/context/test_sources_series.py::test_the_derivative_symbols_of_a_venue_are_the_perpetuals_its_series_are_shown`
    - `tests/unit/context/test_sources_series.py::test_the_market_type_of_a_series_is_asked_by_venue_and_symbol`
    - `tests/unit/context/test_sources_series.py::test_the_series_list_and_the_perpetual_mapping_name_the_same_series`
    - `tests/unit/context/test_sources_series.py::test_the_series_list_names_every_market_the_deployment_ingests_with_its_type`
    - `tests/unit/crossvenue/test_consensus_write.py::test_every_spot_group_of_the_deployment_has_two_venues_and_an_alias_under_each_symbol`
    - `tests/unit/crossvenue/test_consensus_write.py::test_two_spot_venues_give_a_consensus_stored_under_both_symbols`
    - `tests/unit/pipeline/test_context_main.py::test_the_book_symbols_are_the_venues_own_series_and_the_derivative_symbols_its_perpetuals`
- **Code:**
    - `src/channelflow/context/book.py`
    - `src/channelflow/context/sources.py`
    - `src/channelflow/crossvenue/deployment.py`
    - `src/channelflow/pipeline/context_main.py`
- **Outcomes:** [[OUT-2026-10-11-implement-second-spot-venue]], [[OUT-2026-10-11-spec-second-spot-venue]]
<!-- trace:end -->

## Notes

Cost, stated: three more series make the worker's cycle longer (it fits channels and signals for every series and every
timeframe); the notary's batches carry more records. Both are consequences of having more series, not of this design.
