---
id: REQ-WP-003
title: Binance connector
type: work-package
prd_ref: "WP-003 Binance connector"
prd_lines: "6945-6958"
phase: null
status: implemented
depends_on: [REQ-WP-002]
tags: []
---

## Requirement

Requirements:

- reconnect before/at 24h lifecycle;
- ping/pong compliance;
- combined streams configurable;
- trades;
- book deltas;
- mark/funding;
- OI polling;
- liquidations when available;
- error metrics.

## Acceptance

- connector reconnects before/at the 24h stream lifecycle limit;
- connector complies with ping/pong keepalive;
- combined streams are configurable;
- connector delivers trades, book deltas, mark/funding, and OI (polled);
- connector delivers liquidations when available from the venue;
- connector exposes error metrics.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-005-binance-connector]]
- **Tests:**
    - `tests/unit/connectors/binance/test_normalize.py::test_a_depth_update_becomes_a_book_delta`
    - `tests/unit/connectors/binance/test_normalize.py::test_a_missing_field_raises_and_names_it`
    - `tests/unit/connectors/binance/test_normalize.py::test_a_price_keeps_every_digit_the_venue_sent`
    - `tests/unit/connectors/binance/test_normalize.py::test_a_rest_snapshot_becomes_a_book_snapshot`
    - `tests/unit/connectors/binance/test_normalize.py::test_a_venue_millisecond_becomes_exact_nanoseconds`
    - `tests/unit/connectors/binance/test_normalize.py::test_an_aggregate_trade_becomes_a_trade_event`
    - `tests/unit/connectors/binance/test_normalize.py::test_derivatives_state_comes_from_premium_index_and_open_interest`
    - `tests/unit/connectors/binance/test_normalize.py::test_every_recorded_trade_normalizes`
    - `tests/unit/connectors/binance/test_normalize.py::test_the_venue_clock_and_our_clock_stay_apart`
    - `tests/unit/connectors/binance/test_orderbook.py::test_a_missing_delta_makes_the_book_admit_it_is_broken`
    - `tests/unit/connectors/binance/test_orderbook.py::test_a_zero_quantity_level_removes_the_rung`
    - `tests/unit/connectors/binance/test_orderbook.py::test_an_invalid_book_refuses_to_supply_state`
    - `tests/unit/connectors/binance/test_orderbook.py::test_deltas_older_than_the_snapshot_are_discarded`
    - `tests/unit/connectors/binance/test_orderbook.py::test_the_recorded_sequence_leaves_the_book_valid`
    - `tests/unit/connectors/binance/test_session.py::test_a_ping_is_answered`
    - `tests/unit/connectors/binance/test_session.py::test_a_reconnect_demands_a_fresh_snapshot`
    - `tests/unit/connectors/binance/test_session.py::test_each_failure_kind_is_counted`
    - `tests/unit/connectors/binance/test_session.py::test_it_reconnects_before_the_venue_closes_the_stream`
    - `tests/unit/connectors/binance/test_session.py::test_the_stream_set_is_configurable`
- **Code:**
    - `src/channelflow/book/book.py`
    - `src/channelflow/connectors/binance/__init__.py`
    - `src/channelflow/connectors/binance/normalize.py`
    - `src/channelflow/connectors/binance/session.py`
    - `tools/record/binance_capture.py`
- **Outcomes:** [[OUT-2026-09-08-implement-binance-connector]], [[OUT-2026-09-08-plan-binance-connector]], [[OUT-2026-09-08-spec-binance-connector]], [[OUT-2026-09-08-tasks-binance-connector]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
