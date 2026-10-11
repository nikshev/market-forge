---
id: REQ-WP-096
title: "The venue-basis pane has a consensus: the venues' quotes become a consensus mid at every minute close"
type: work-package
prd_ref: "§17.1, §17.3, §27.3; owner's direction 2026-10-11"
prd_lines: "2520-2552, 4423-4436"
phase: null
status: tested
depends_on: [REQ-WP-095, REQ-WP-091]
tags: [consensus, venue-basis, quotes, panes]
hard_gated: false
---

## Requirement

[[REQ-WP-091]] built the consensus line and the venue-basis pane and left them reading "no data" "until the book
subscription exists". The API already merges `venue_basis_bps` from two tables, `quotes` and `consensus`; the
library `crossvenue/consensus.py` computes the median; **nothing writes either table**. [[REQ-WP-095]] writes
`quotes`. This requirement writes `consensus`.

1. **A pass in the worker writes one `consensus` row per (asset, market type) at every minute close**, from the
   `quotes` of the venues of that market type at or before the close, through the existing `consensus_mid`
   (median of fresh mids, a stale or late quote excluded with a reason, fewer than two venues refused). Every
   timeframe's bar close is also a minute close, so one cadence serves every timeframe the chart can show.
2. **A refusal is stored, not skipped**: the row exists with its `refusal_reason` and no price, because the line's
   absence has to be explainable ([[REQ-WP-091]]).
3. **The asset of a venue's symbol comes from the registry** (`crossvenue/consensus.py`'s `AssetRegistry`), the
   same one the API uses, so the writer and the reader cannot disagree about which venues are one asset.

What the deployment's own venues allow, stated rather than discovered later: Bybit and OKX are both perpetuals of
the same pair, so **BTC has a perpetual consensus of two venues, and the pane works for those two series**.
Binance's series are spot markets, and no other spot venue is ingested, so **a spot consensus has one venue and
is refused**: the Binance panes say so. Making them live needs a second spot venue; adding one (for example OKX
`BTC-USDT` spot, trades only, the same ingest image) is an option this requirement records and does not decide.

## Acceptance

- For a fixture of quotes from two and from three venues the stored consensus equals the median; a stale quote
  and a later quote are excluded with a reason; one venue stores a refusal row with a reason and no price.
- The consensus at a minute close is unchanged when quotes after it are appended (a test).
- The pass is idempotent: running it over the same range twice stores each close once.
- On the running stack, `GET` of the venue-basis read for Bybit and OKX BTC returns points whose value equals
  `10000 * (mid_i / consensus_mid - 1)` for the stored mids, and the Binance read returns the refusal reason
  instead of a number. The recorded query shows both.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-148-consensus-producer]]
- **Tests:**
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_failed_commit_is_reported_and_the_rows_come_back_next_pass`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_gap_in_the_quotes_is_a_run_of_refusal_rows_not_a_hole`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_quote_after_the_close_cannot_change_the_consensus_at_it`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_spot_group_of_one_venue_stores_a_refusal_every_minute`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_spot_series_reads_back_a_refusal_and_no_basis`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_stale_quote_does_not_contribute_and_the_count_says_so`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_venue_that_has_gone_quiet_for_good_stops_holding_the_pass_back`
    - `tests/unit/crossvenue/test_consensus_write.py::test_a_venue_that_lags_holds_the_pass_back_so_no_row_leaves_it_out`
    - `tests/unit/crossvenue/test_consensus_write.py::test_an_empty_quotes_table_is_a_pass_that_writes_nothing`
    - `tests/unit/crossvenue/test_consensus_write.py::test_bybit_and_okx_btc_are_one_asset_and_eth_is_another`
    - `tests/unit/crossvenue/test_consensus_write.py::test_each_group_is_stored_under_every_symbol_its_members_use_so_either_chart_finds_it`
    - `tests/unit/crossvenue/test_consensus_write.py::test_each_symbol_resumes_from_its_own_watermark`
    - `tests/unit/crossvenue/test_consensus_write.py::test_no_quotes_at_all_writes_nothing`
    - `tests/unit/crossvenue/test_consensus_write.py::test_one_venue_is_a_refusal_with_its_reason_and_no_price`
    - `tests/unit/crossvenue/test_consensus_write.py::test_the_deployments_markets_group_by_asset_and_market_type_never_blended`
    - `tests/unit/crossvenue/test_consensus_write.py::test_the_pass_is_idempotent_and_resumes_from_its_watermark`
    - `tests/unit/crossvenue/test_consensus_write.py::test_the_pass_writes_the_table_and_a_second_pass_writes_nothing`
    - `tests/unit/crossvenue/test_consensus_write.py::test_the_staleness_bound_is_inclusive`
    - `tests/unit/crossvenue/test_consensus_write.py::test_three_venues_give_the_middle_one`
    - `tests/unit/crossvenue/test_consensus_write.py::test_two_venues_give_the_interpolated_median`
    - `tests/unit/crossvenue/test_consensus_write.py::test_what_is_stored_reads_back_as_the_venue_basis_formula_for_both_perpetual_venues`
- **Outcomes:** [[OUT-2026-10-11-implement-consensus-producer]], [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

`venue_basis_bps` stays a read-time merge in the API ([[REQ-WP-091]]'s design). It is not duplicated into
`feature_snapshots`, so there is one place to correct it.
