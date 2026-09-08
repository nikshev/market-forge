---
id: REQ-WP-005
title: Bar aggregation
type: work-package
prd_ref: "WP-005 Bar aggregation"
prd_lines: "6968-6974"
phase: null
status: implemented
depends_on: [REQ-WP-002, REQ-WP-003]
tags: []
---

## Requirement

- event-time windows;
- late-event policy;
- finalized bar callback;
- trade-side aggregates.

## Acceptance

- bars aggregate on event-time windows;
- a late-event policy is enforced;
- a finalized-bar callback fires on close;
- trade-side aggregates are produced per bar.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-006-bar-aggregation]]
- **Tests:**
    - `tests/unit/bars/test_bar_fields.py::test_a_bar_carries_every_field_prd_section_12_lists`
    - `tests/unit/bars/test_bar_fields.py::test_open_and_close_follow_event_time_not_arrival`
    - `tests/unit/bars/test_bar_fields.py::test_vwap_is_exact_for_a_price_beyond_double_precision`
    - `tests/unit/bars/test_determinism.py::test_shuffled_trades_produce_identical_bars`
    - `tests/unit/bars/test_determinism.py::test_the_builder_cannot_consult_a_clock`
    - `tests/unit/bars/test_finalization.py::test_a_trade_for_a_finalized_bar_is_discarded_and_counted`
    - `tests/unit/bars/test_finalization.py::test_a_trade_inside_the_grace_period_is_included`
    - `tests/unit/bars/test_finalization.py::test_a_watermark_jump_finalizes_every_window_in_order`
    - `tests/unit/bars/test_finalization.py::test_a_window_with_no_trades_produces_no_bar`
- **Code:**
    - `src/channelflow/bars/__init__.py`
    - `src/channelflow/bars/builder.py`
    - `src/channelflow/bars/models.py`
- **Outcomes:** [[OUT-2026-09-08-implement-bar-aggregation]], [[OUT-2026-09-08-plan-bar-aggregation]], [[OUT-2026-09-08-spec-bar-aggregation]], [[OUT-2026-09-08-tasks-bar-aggregation]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
