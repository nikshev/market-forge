---
id: REQ-STORE-002
title: The API's reads, served from the canonical plane
type: work-package
prd_ref: "§29.5 feature_snapshots, §29.6 channel_snapshots, §29.7 signals, §28 API"
prd_lines: "4649-4675, 4461-4543"
phase: null
status: implemented
depends_on: ["REQ-STORE-001", "REQ-TBL-001", "REQ-API-001"]
tags: []
hard_gated: false
---

## Requirement

[[ADR-019]] made the API depend on a repository port rather than a database, and
said why:

> PRD §29 defines where those live — Iceberg tables on object storage, Pinot for
> HOT serving, PostgreSQL for metadata. None of it is built, and REQ-WP-009's
> chart cannot wait for it. So the API depends on a protocol. The in-memory
> implementation serves it now; the durable one arrives with section 29 and
> replaces it **without any endpoint changing**.

PRD §29.5:

> Prefer wide table for stable production feature set plus optional long table
> for experimental registry.

PRD §29.6:

> Immutable append-only. Important columns: as_of; model/version; lookback;
> lower/center/upper; slope; width; quality components; forecast arrays;
> source_max_event_time.

PRD §29.7:

> Immutable decision core plus separate resolution/outcome table. Never update
> original feature values after signal.

## Acceptance

- every read the port declares is served from canonical tables;
- the two implementations answer alike, checked by one suite run against both
  rather than asserted;
- every existing endpoint test passes against both, so "no endpoint changes" is
  a property the suite fails on rather than a claim;
- a channel snapshot is never later than the instant asked for;
- a channel snapshot's quality components and forecast array survive the round
  trip;
- a signal's transition history comes back in the order it happened, whatever
  order the rows arrive in;
- a signal is reachable by the same id its alert's deep link uses;
- a score's contributions belong to that score and not to another taken at the
  same instant;
- the newest score for a market is the one returned;
- a market nobody scored has no score, rather than an empty one;
- an empty repository answers every read without raising.

## Scope

**In:** the `channel_snapshots`, `feature_snapshots`, `signals`,
`signal_transitions`, `markets`, `setup_scores` and `score_contributions`
tables, their mappings, and the repository over them.

**Out, and named rather than silently dropped:**

- **Retiring the in-memory repository.** It is the fixture every test builds and
  the fastest thing to run; the point of a port is that both exist.
- **Writing from a live pipeline.** The repository's writers exist for tests and
  for a backfill; a process that fills the tables from a feed is deployment
  work.
- **PRD §29.7's resolution/outcome table.** §29.7 asks for the decision core
  *plus* a separate outcome table; [[REQ-BT-001]] models outcomes and nothing
  joins them to signals yet.
- **PostgreSQL (§30).** Control plane, not lineage.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-055-lakehouse-repository]]
- **Tests:**
    - `tests/unit/api/test_repository_conformance.py::test_a_bar_round_trips_with_its_decimals[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_bar_round_trips_with_its_decimals[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_channel_snapshot_is_never_later_than_the_instant_asked_for[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_channel_snapshot_is_never_later_than_the_instant_asked_for[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_channel_snapshot_survives_its_quality_and_its_forecast[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_channel_snapshot_survives_its_quality_and_its_forecast[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_list_filters_on_both_fields[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_list_filters_on_both_fields[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_nobody_scored_has_no_score[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_nobody_scored_has_no_score[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_score_round_trips_with_its_contributions[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_score_round_trips_with_its_contributions[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_signal_is_reachable_by_the_id_its_deep_link_uses[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_signal_is_reachable_by_the_id_its_deep_link_uses[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_signal_round_trips_with_its_history_in_order[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_signal_round_trips_with_its_history_in_order[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_snapshot_for_another_series_is_not_returned[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_snapshot_for_another_series_is_not_returned[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_an_empty_repository_answers_every_read_without_raising[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_an_empty_repository_answers_every_read_without_raising[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_bars_can_be_bounded_at_both_ends[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_bars_can_be_bounded_at_both_ends[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_bars_come_back_in_time_order_and_the_limit_takes_the_newest[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_bars_come_back_in_time_order_and_the_limit_takes_the_newest[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_feature_points_are_bounded_at_both_ends[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_feature_points_are_bounded_at_both_ends[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_feature_points_come_back_grouped_by_instant[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_feature_points_come_back_grouped_by_instant[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_signals_filter_on_every_field_the_port_offers[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_signals_filter_on_every_field_the_port_offers[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_the_latest_score_is_the_one_returned[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_the_latest_score_is_the_one_returned[lakehouse]`
    - `tests/unit/tables/test_mapping.py::test_a_boolean_is_not_an_integer_here_either`
    - `tests/unit/tables/test_mapping.py::test_a_decimal_column_refuses_anything_but_its_exact_text`
    - `tests/unit/tables/test_mapping.py::test_a_map_column_reads_from_either_shape`
    - `tests/unit/tables/test_mapping.py::test_a_transition_history_is_restored_by_its_ordinal`
    - `tests/unit/tables/test_mapping.py::test_feature_rows_do_not_depend_on_a_mapping_s_insertion_order`
    - `tests/unit/tables/test_mapping.py::test_the_row_helpers_refuse_across_kinds`
    - `tests/unit/tables/test_mapping.py::test_two_different_scores_get_two_different_ids`
- **Code:**
    - `src/channelflow/api/lakehouse_repository.py`
    - `src/channelflow/tables/channels.py`
    - `src/channelflow/tables/features.py`
    - `src/channelflow/tables/rows.py`
    - `src/channelflow/tables/signals.py`
- **Outcomes:** [[OUT-2026-09-09-implement-lakehouse-repository]], [[OUT-2026-09-09-plan-lakehouse-repository]], [[OUT-2026-09-09-requirement-lakehouse-repository]], [[OUT-2026-09-09-spec-lakehouse-repository]]
<!-- trace:end -->

## Notes

Hand-written: PRD §46 has no work package for §29's tables. This section is human
territory and is never machine-rewritten.
