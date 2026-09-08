---
id: REQ-WP-016
title: Cross-venue
type: work-package
prd_ref: "WP-016 Cross-venue"
prd_lines: "7049-7054"
phase: null
status: implemented
depends_on: ["REQ-ASSET-001", "REQ-WP-004", "REQ-WP-015"]
tags: []
---

## Requirement

- canonical instrument mapping;
- consensus price;
- basis.

## Acceptance

Consensus price (§17.1):

- a consensus mid is the median of normalized mids across the selected venues,
  and the result names the venues that contributed;
- a venue whose mid is missing, or older than a configurable staleness
  tolerance at the instant asked about, does not contribute, and the
  contributor count is reported;
- a consensus over fewer than two contributing venues is refused.

Basis (§17.3, §18.14):

- `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)` is computed for
  each contributing venue;
- mid-based basis is refused when either side is an AMM, and
  `executable_basis_bps(N)` is computed instead, from executable prices at a
  notional supplied by the caller.

Lead-lag (§17.2):

- per-venue returns over 1/5/10 s windows and pairwise lagged correlations are
  computed from data available at the instant asked about;
- lead-lag outputs are marked research-only, and no signal-path module imports
  them, asserted over the source.

Fragmentation and liquidity (§17.4):

- depth by venue at 10/25/50 bps is reported, each venue measured by its own
  executable-depth measure;
- the best effective execution venue for a fixed notional is identified from
  all-in cost, not from top-of-book price;
- liquidity concentration across venues is reported.

Throughout:

- every output is computed from data available at the instant asked about; no
  venue's later value is used.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-023-cross-venue]]
- **Tests:**
    - `tests/unit/crossvenue/test_consensus.py::test_a_quote_from_after_the_instant_does_not_contribute`
    - `tests/unit/crossvenue/test_consensus.py::test_a_quote_the_registry_does_not_know_is_refused`
    - `tests/unit/crossvenue/test_consensus.py::test_a_stale_venue_does_not_contribute`
    - `tests/unit/crossvenue/test_consensus.py::test_an_even_count_reports_that_the_median_is_interpolated`
    - `tests/unit/crossvenue/test_consensus.py::test_basis_matches_the_formula`
    - `tests/unit/crossvenue/test_consensus.py::test_every_venue_stale_is_refused_not_zero`
    - `tests/unit/crossvenue/test_consensus.py::test_executable_basis_compares_prices_at_one_size`
    - `tests/unit/crossvenue/test_consensus.py::test_executable_basis_refuses_an_impossible_reference`
    - `tests/unit/crossvenue/test_consensus.py::test_fewer_than_two_contributors_is_refused`
    - `tests/unit/crossvenue/test_consensus.py::test_mid_basis_is_refused_for_an_amm`
    - `tests/unit/crossvenue/test_consensus.py::test_the_consensus_is_the_median_and_names_its_contributors`
    - `tests/unit/crossvenue/test_consensus.py::test_venues_are_comparable_through_the_registry_not_their_tickers`
    - `tests/unit/crossvenue/test_consensus.py::test_venues_quoting_different_assets_are_refused`
    - `tests/unit/crossvenue/test_fragmentation.py::test_a_tie_breaks_deterministically`
    - `tests/unit/crossvenue/test_fragmentation.py::test_a_venue_missing_a_band_is_simply_absent`
    - `tests/unit/crossvenue/test_fragmentation.py::test_a_venue_that_cannot_fill_is_excluded_and_reported`
    - `tests/unit/crossvenue/test_fragmentation.py::test_an_empty_venue_list_is_refused`
    - `tests/unit/crossvenue/test_fragmentation.py::test_concentration_rises_as_liquidity_gathers`
    - `tests/unit/crossvenue/test_fragmentation.py::test_no_depth_anywhere_is_not_concentrated`
    - `tests/unit/crossvenue/test_fragmentation.py::test_no_venue_able_to_fill_is_refused`
    - `tests/unit/crossvenue/test_fragmentation.py::test_one_venue_is_maximum_concentration`
    - `tests/unit/crossvenue/test_fragmentation.py::test_the_best_venue_is_chosen_by_all_in_cost_not_headline_price`
    - `tests/unit/crossvenue/test_fragmentation.py::test_the_crossvenue_package_cannot_consult_a_clock`
    - `tests/unit/crossvenue/test_fragmentation.py::test_the_depth_table_covers_the_bands_the_prd_names`
    - `tests/unit/crossvenue/test_leadlag.py::test_a_constant_series_gives_no_correlation`
    - `tests/unit/crossvenue/test_leadlag.py::test_a_lagged_correlation_aligns_the_series`
    - `tests/unit/crossvenue/test_leadlag.py::test_a_negative_lag_is_refused`
    - `tests/unit/crossvenue/test_leadlag.py::test_a_return_measures_the_window`
    - `tests/unit/crossvenue/test_leadlag.py::test_a_return_uses_only_prices_at_or_before_the_instant`
    - `tests/unit/crossvenue/test_leadlag.py::test_a_window_with_nothing_to_open_against_is_absent_not_zero`
    - `tests/unit/crossvenue/test_leadlag.py::test_every_output_declares_itself_research_only`
    - `tests/unit/crossvenue/test_leadlag.py::test_every_window_the_prd_names_is_available`
    - `tests/unit/crossvenue/test_leadlag.py::test_lead_lag_is_not_re_exported_from_the_package_root`
    - `tests/unit/crossvenue/test_leadlag.py::test_no_signal_path_module_imports_lead_lag`
    - `tests/unit/crossvenue/test_leadlag.py::test_the_signal_path_packages_all_exist`
    - `tests/unit/crossvenue/test_leadlag.py::test_too_few_pairs_gives_no_correlation`
- **Code:**
    - `src/channelflow/crossvenue/__init__.py`
    - `src/channelflow/crossvenue/consensus.py`
    - `src/channelflow/crossvenue/fragmentation.py`
    - `src/channelflow/crossvenue/leadlag.py`
    - `src/channelflow/crossvenue/models.py`
- **Outcomes:** [[OUT-2026-09-08-implement-cross-venue]], [[OUT-2026-09-08-plan-cross-venue]], [[OUT-2026-09-08-requirement-cross-venue-acceptance]], [[OUT-2026-09-08-spec-cross-venue]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.

The acceptance criteria above replaced an `ACCEPTANCE-NOT-SPECIFIED` marker on
2026-09-08. PRD §17 describes the engine in four subsections and states no
acceptance criteria of its own; the criteria were derived from those subsections
and approved by the repository owner. The derivation, the alternatives
considered and the reasoning for each criterion are in
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`.

Two points that document settles and this note should not restate in full:

- **"Canonical instrument mapping" is not defined in §17.** It is §18.13's asset
  registry, extracted as `REQ-ASSET-001`, which this requirement now depends on.
- **§17.3's mid-based basis and §18.14's executable basis are both required,
  under different names.** §18.14 forbids comparing a CEX top-of-book quote
  against an AMM spot quote, so the mid-based figure is refused for any pair
  involving an AMM rather than computed with a caption.

Scope deliberately excludes a second CEX connector: no work package in the PRD
builds one, and Bybit and OKX are named in §17.2 without appearing in the
work-package list. Binance and Uniswap v3 are two venues, and enough to exercise
every criterion.
