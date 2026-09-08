---
id: REQ-WP-002
title: Domain model
type: work-package
prd_ref: "WP-002 Domain model"
prd_lines: "6937-6944"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Implement all canonical events as immutable/frozen Pydantic models where practical.

Done when:

- serialization fixtures stable.

## Acceptance

- serialization fixtures stable.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-004-domain-model]]
- **Tests:**
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[book_delta]`
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[book_snapshot]`
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[derivatives_state]`
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[dex_liquidity]`
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[dex_swap]`
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[liquidation]`
    - `tests/unit/domain/test_fixtures.py::test_every_kind_round_trips[trade]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[book_delta]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[book_snapshot]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[derivatives_state]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[dex_liquidity]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[dex_swap]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[liquidation]`
    - `tests/unit/domain/test_fixtures.py::test_serialization_matches_the_committed_fixture[trade]`
    - `tests/unit/domain/test_identity.py::test_a_dex_log_is_identified_by_chain_tx_and_log_index`
    - `tests/unit/domain/test_identity.py::test_a_different_trade_id_is_a_different_identity`
    - `tests/unit/domain/test_identity.py::test_the_same_trade_received_twice_has_one_identity`
    - `tests/unit/domain/test_precision_policy.py::test_a_venue_price_times_a_quantity_keeps_every_digit`
    - `tests/unit/domain/test_precision_policy.py::test_division_is_still_not_claimed_to_be_exact`
    - `tests/unit/domain/test_precision_policy.py::test_the_precision_policy_is_applied_on_import`
    - `tests/unit/domain/test_round_trip.py::test_a_decimal_beyond_double_precision_survives`
    - `tests/unit/domain/test_round_trip.py::test_a_nanosecond_timestamp_survives_a_double_parsing_consumer`
    - `tests/unit/domain/test_round_trip.py::test_event_meta_round_trips_exactly`
    - `tests/unit/domain/test_round_trip.py::test_serializing_twice_is_byte_identical`
    - `tests/unit/domain/test_validation.py::test_a_book_level_may_have_zero_quantity`
    - `tests/unit/domain/test_validation.py::test_a_constructed_event_cannot_be_mutated`
    - `tests/unit/domain/test_validation.py::test_a_negative_trade_price_is_rejected`
    - `tests/unit/domain/test_validation.py::test_an_aggressor_side_outside_the_permitted_set_is_rejected`
    - `tests/unit/domain/test_validation.py::test_an_unknown_field_is_rejected`
    - `tests/unit/domain/test_validation.py::test_omitting_ingest_time_is_rejected_and_the_field_is_named`
- **Code:**
    - `src/channelflow/__init__.py`
    - `src/channelflow/domain/__init__.py`
    - `src/channelflow/domain/book.py`
    - `src/channelflow/domain/defi.py`
    - `src/channelflow/domain/derivatives.py`
    - `src/channelflow/domain/meta.py`
    - `src/channelflow/domain/serialization.py`
    - `src/channelflow/domain/trades.py`
- **Outcomes:** [[OUT-2026-09-07-implement-domain-model]], [[OUT-2026-09-07-plan-domain-model]], [[OUT-2026-09-07-spec-domain-model]], [[OUT-2026-09-07-tasks-domain-model]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
