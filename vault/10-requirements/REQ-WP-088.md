---
id: REQ-WP-088
title: "CVD and the trade-imbalance features are produced from the aggressor volumes the bars already carry, and the CVD pane draws them"
type: work-package
prd_ref: "§15.4, §27.3, §29.5"
prd_lines: "2386-2403, 4423-4436"
phase: null
status: implemented
depends_on: [REQ-WP-011, REQ-STORE-002, REQ-WP-027, REQ-WP-084]
tags: [features, cvd, ingest, pipeline, web]
hard_gated: false
---

## Requirement

PRD §15.4 defines trade imbalance and cumulative volume delta:

`delta_t = aggressive_buy_notional - aggressive_sell_notional`

`CVD_t = CVD_{t-1} + delta_t`

with the features: delta per bar; CVD slope; CVD-price divergence; CVD acceleration; normalized delta / total
volume. §27.3 lists CVD as a selectable lower pane.

The code that computes them exists (`features/flow.py`, [[REQ-WP-011]]), over trades, in notional. **Nothing runs it.**
Checked on 2026-10-04: the features table has no rows and `/features/snapshot` returns `{}`, so the CVD pane reads
"no data" ([[REQ-WP-084]]), which is true.

**The data is already stored, in another form.** Every bar in the lakehouse carries the split by aggressor side:
`aggressive_buy_base`, `aggressive_sell_base`, `delta_base`, `trade_count`, `first_trade_id`, `last_trade_id`
(`resample` sums them for every timeframe, from complete windows). The API does not expose them. They are in **base
units**; PRD §15.4 says notional, and the bar stores only the quote total, so this requirement produces the
features **in base units, under `*_base` names**, recorded as a knowing deviation in [[ADR-068]] with the way back.

This requirement derives the §15.4 features from those stored bars, per timeframe, in the worker pass that already
reads them, writes them to the features table, and serves them through the existing `/features/*` routes, so the CVD
pane draws a line.

- **One pure function for every pass and replay** (Principle VII): the features are a function of the bars.
- **No look-ahead** (Principle I): a feature at bar time `t` uses only bars at or before `t`; a forming bar produces none.
- **Append-only and idempotent**: a second pass over the same bars writes no second row; a writer reads before it
  writes (ADR-056).
- **CVD is a running sum, so a break must end it.** A missing bar, or (where the venue's trade ids are sequential:
  Binance, measured; Bybit and OKX are not) a missed trade, makes every later value wrong by an unknown amount. The
  sum is kept within a **run** of consecutive bars; a break starts the next at zero; the chart breaks the line at it.
- **OFI and book features are not here**: §15.3 needs a top-of-book subscription, which the ingest does not have.

## Acceptance

- For a fixture of bars with known aggressor volumes, the rows written for a bar are: `delta_base` buy minus sell,
  `cvd_base` the running sum within the run, `normalized_delta_base` the delta over `volume_base` (absent, not zero,
  when nothing traded), `cvd_base_slope`, and `cvd_base_acceleration` (absent in a run's first bar). No row is
  named `cvd` or `delta_notional`.
- A feature at bar time `t` is unchanged when bars later than `t` are appended (a test, as for the other features:
  [[REQ-NRT-LEAK]]'s family); a forming bar produces none.
- A missing bar ends the run: removing the middle of three bars gives two runs and no sum across the gap. For
  Binance a trade-id jump between bars ends it too, and a bar whose id span differs from its `trade_count` produces
  no row; Bybit and OKX break on a missing bar only (measured limit).
- A second worker pass over the same bars writes no duplicate row, for every timeframe the worker processes.
- The same bars give the same rows in any order and in any pass (one pure function).
- On the running stack, after deployment, `/api/v1/features/timeseries` for `binance` `BTCUSDT` at 15m returns
  `cvd_base`, and the "CVD (base)" pane draws a line from it, broken where the run changes; a screenshot of the
  live pane, light and dark, is kept under `docs/ui/` and looked at.
- The deviation from PRD §15.4 (base units, not notional) is recorded in [[ADR-068]] with the way back.
- CVD-price divergence is not produced (ADR-013 stands).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-135-trade-flow-features]]
- **Tests:**
    - `tests/unit/features/test_flow_bars.py::test_a_bar_where_nothing_traded_has_no_normalized_delta_and_is_not_a_break`
    - `tests/unit/features/test_flow_bars.py::test_a_bar_whose_id_span_differs_from_its_trade_count_has_no_row_and_breaks_both_sides`
    - `tests/unit/features/test_flow_bars.py::test_a_forming_bar_produces_no_row`
    - `tests/unit/features/test_flow_bars.py::test_a_missing_bar_ends_the_run_and_nothing_is_summed_across_it`
    - `tests/unit/features/test_flow_bars.py::test_a_trade_id_jump_between_bars_ends_the_run_for_a_sequential_venue`
    - `tests/unit/features/test_flow_bars.py::test_a_venue_without_sequential_ids_breaks_only_on_a_missing_bar`
    - `tests/unit/features/test_flow_bars.py::test_appending_later_bars_leaves_the_earlier_rows_unchanged`
    - `tests/unit/features/test_flow_bars.py::test_delta_and_cvd_are_hand_computed_for_three_bars`
    - `tests/unit/features/test_flow_bars.py::test_each_timeframe_has_its_own_runs`
    - `tests/unit/features/test_flow_bars.py::test_no_bars_give_no_rows`
    - `tests/unit/features/test_flow_bars.py::test_normalized_delta_is_the_delta_over_the_bars_volume`
    - `tests/unit/features/test_flow_bars.py::test_slope_is_delta_over_seconds_and_acceleration_is_absent_in_a_runs_first_bar`
    - `tests/unit/features/test_flow_bars.py::test_the_feature_names_are_the_six_base_names_and_never_the_notional_ones`
    - `tests/unit/features/test_flow_bars.py::test_the_first_bar_of_a_new_run_has_no_acceleration_either`
    - `tests/unit/features/test_flow_bars.py::test_the_order_the_bars_arrive_in_does_not_matter`
    - `tests/unit/features/test_flow_registry.py::test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated[cvd_base]`
    - `tests/unit/features/test_flow_registry.py::test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated[cvd_base_acceleration]`
    - `tests/unit/features/test_flow_registry.py::test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated[cvd_base_slope]`
    - `tests/unit/features/test_flow_registry.py::test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated[cvd_run]`
    - `tests/unit/features/test_flow_registry.py::test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated[delta_base]`
    - `tests/unit/features/test_flow_registry.py::test_every_flow_feature_is_registered_with_its_unit_and_the_deviation_stated[normalized_delta_base]`
    - `tests/unit/features/test_flow_registry.py::test_only_binance_is_flagged_as_having_sequential_trade_ids`
    - `tests/unit/pipeline/test_channel_flow_step.py::test_a_failing_flow_step_does_not_stop_the_channel_step`
    - `tests/unit/pipeline/test_channel_flow_step.py::test_a_pass_writes_the_flow_rows_and_a_second_pass_writes_nothing`
    - `tests/unit/pipeline/test_channel_flow_step.py::test_the_channel_step_still_gets_the_bars_it_always_got`
    - `tests/unit/pipeline/test_channel_flow_step.py::test_the_flow_step_writes_every_timeframe_the_bars_table_has`
    - `tests/unit/tables/test_flow_sink.py::test_a_longer_series_appends_only_what_is_after_the_latest_row`
    - `tests/unit/tables/test_flow_sink.py::test_a_shorter_series_writes_nothing_and_never_rewrites`
    - `tests/unit/tables/test_flow_sink.py::test_rows_are_written_and_a_second_pass_over_the_same_bars_writes_nothing`
    - `tests/unit/tables/test_flow_sink.py::test_two_series_do_not_see_each_others_latest_row`
    - `tests/unit/web/test_cvd_pane_artifacts.py::test_every_module_this_requirement_touches_names_it[FlowPane.tsx]`
    - `tests/unit/web/test_cvd_pane_artifacts.py::test_every_module_this_requirement_touches_names_it[panes.ts]`
    - `tests/unit/web/test_cvd_pane_artifacts.py::test_the_cvd_pane_names_a_feature_the_worker_writes`
    - `tests/unit/web/test_cvd_pane_artifacts.py::test_there_is_a_live_screenshot_of_the_cvd_pane_in_each_scheme[dark]`
    - `tests/unit/web/test_cvd_pane_artifacts.py::test_there_is_a_live_screenshot_of_the_cvd_pane_in_each_scheme[light]`
- **Code:**
    - `apps/web/src/FlowPane.tsx`
    - `apps/web/src/panes.ts`
    - `src/channelflow/connectors/venue.py`
    - `src/channelflow/features/__init__.py`
    - `src/channelflow/pipeline/channel_main.py`
    - `src/channelflow/tables/features.py`
- **Outcomes:** [[OUT-2026-10-04-implement-trade-flow-features]], [[OUT-2026-10-04-plan-trade-flow-features]], [[OUT-2026-10-04-spec-trade-flow-features]], [[OUT-2026-10-04-tasks-trade-flow-features]]
<!-- trace:end -->

## Notes

Raised by the owner on 2026-10-04 ("these data should already be there"). The first reading was that the trades were
not stored and a trade-level producer was needed. Reading the bars table showed they are not needed: the aggressor
split, the trade count and the first and last trade id are stored per bar, at every timeframe, and have been since
each series' ingest started. The unit is base, not notional, which is the whole of the deviation ([[ADR-068]]).

[[REQ-WP-089]] (the volume profile with buy and sell by price level) is different: it needs trades by price, and a
bar does not carry them. It will need a trade intake of its own, which this requirement no longer provides.
