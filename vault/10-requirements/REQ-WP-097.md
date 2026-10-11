---
id: REQ-WP-097
title: "Every lower pane the running deployment can fill has data, and the ones it cannot say why"
type: work-package
prd_ref: "§27.3, §45 Phase 2, §45 Phase 3; owner's direction 2026-10-11"
prd_lines: "4423-4436, 6751, 6768"
phase: null
status: tested
depends_on: [REQ-WP-093, REQ-WP-094, REQ-WP-095, REQ-WP-096, REQ-WP-084]
tags: [panes, acceptance, deployment]
hard_gated: false
---

## Requirement

The owner's ask of 2026-10-11 was "make all the data display". Four requirements build the producers
([[REQ-WP-093]], [[REQ-WP-094]], [[REQ-WP-095]], [[REQ-WP-096]]); this one is the acceptance of the whole, on the
**deployed** stack, so that "every pane has data" is a recorded measurement and not a belief.

For every market the deployment lists and every timeframe the page offers, each of the ten lower panes (volume
and CVD from the bars, and the nine feature panes of §27.3 plus the depth-imbalance extra) is in exactly one of
three states, and the state is checked against the API:

- **has data**: at least one point in the loaded range;
- **absent for a stated reason that is true**: a spot market has no perpetual consensus; a symbol with no
  liquidation in the range; a DEX pane on a series with no DEX source;
- **never** "absent because the producer is not deployed" -- that is the state this requirement removes.

## Acceptance

- A recorded run (a script kept in `tools/`, its output in the outcome note) queries `/api/v1/features/timeseries`
  and the venue-basis read for every listed market and timeframe and prints the three-state table above. Any cell
  whose reason is "no producer" fails the run.
- The running containers are the ones the commits describe: the collector services are up, healthy, and have been
  for a measured interval; the worker's image was built from a clean committed tree.
- A screenshot of a chart with the pane row enabled is kept under `docs/ui/` and looked at, light and dark
  ([[REQ-WP-091]]'s own acceptance asks the same).
- DEX panes are listed by name with their state; if they are not built (a further requirement, if the owner asks for
  it) the table says "no DEX source" for them, which is a true reason and not a hidden one.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-149-pane-coverage]]
- **Tests:**
    - `tests/tools/panes/test_classify.py::test_a_cell_with_no_producer_makes_the_report_fail_and_names_the_pane`
    - `tests/tools/panes/test_classify.py::test_a_dex_pane_that_has_data_is_data_whatever_the_deployment_says`
    - `tests/tools/panes/test_classify.py::test_a_markets_read_that_fails_is_unreachable_even_if_the_other_reads_answer`
    - `tests/tools/panes/test_classify.py::test_a_page_with_no_panes_is_an_error_not_an_empty_report`
    - `tests/tools/panes/test_classify.py::test_a_pane_with_a_point_is_data`
    - `tests/tools/panes/test_classify.py::test_a_pane_with_no_point_and_no_reason_is_no_producer`
    - `tests/tools/panes/test_classify.py::test_a_refused_consensus_is_reported_as_the_reason_the_api_stored`
    - `tests/tools/panes/test_classify.py::test_an_api_that_answers_the_markets_read_with_an_error_is_unreachable_not_an_empty_table`
    - `tests/tools/panes/test_classify.py::test_an_api_that_cannot_be_reached_exits_two_and_prints_no_table`
    - `tests/tools/panes/test_classify.py::test_every_cell_data_or_reasoned_exits_zero`
    - `tests/tools/panes/test_classify.py::test_every_market_and_every_chosen_timeframe_is_queried_and_none_is_invented`
    - `tests/tools/panes/test_classify.py::test_liquidations_with_covered_windows_and_no_event_are_absent_for_a_true_reason`
    - `tests/tools/panes/test_classify.py::test_liquidations_with_no_covered_window_are_no_producer`
    - `tests/tools/panes/test_classify.py::test_only_real_numbers_count_as_a_value`
    - `tests/tools/panes/test_classify.py::test_only_the_chosen_timeframes_are_queried`
    - `tests/tools/panes/test_classify.py::test_the_dex_panes_are_absent_with_the_one_reason_the_module_states`
    - `tests/tools/panes/test_classify.py::test_the_imbalance_having_points_is_data_even_with_no_sums`
    - `tests/tools/panes/test_classify.py::test_the_panes_are_read_from_the_page_with_volume_first`
    - `tests/tools/panes/test_classify.py::test_the_range_asked_for_ends_now_and_starts_the_stated_hours_before`
    - `tests/tools/panes/test_classify.py::test_venue_basis_whose_consensus_read_failed_is_no_producer_and_says_what_it_answered`
    - `tests/tools/panes/test_classify.py::test_venue_basis_with_a_stored_refusal_is_absent_with_the_stored_reason`
    - `tests/tools/panes/test_classify.py::test_venue_basis_with_consensus_rows_but_no_basis_is_no_producer_not_absent`
    - `tests/tools/panes/test_classify.py::test_volume_is_read_from_the_bars_not_from_a_feature`
- **Outcomes:** [[OUT-2026-10-11-implement-pane-coverage]], [[OUT-2026-10-11-plan-live-panes]], [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

This is deliberately a requirement about the deployment. A green unit suite proved the six trade features and
said nothing about the nine panes that were empty for a month.
