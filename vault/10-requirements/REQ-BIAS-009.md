---
id: REQ-BIAS-009
title: Fees/slippage must be included in economic evaluation.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5325-5325"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Fees/slippage must be included in economic evaluation.

## Acceptance

Fees/slippage must be included in economic evaluation.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-019-adaptive-stops]]
- **Tests:**
    - `tests/unit/stops/test_replay.py::test_realized_r_is_net_of_fees_and_slippage`
    - `tests/unit/stops/test_replay.py::test_slippage_is_always_adverse`
- **Code:**
    - `src/channelflow/stops/replay.py`
- **Outcomes:** [[OUT-2026-09-08-implement-adaptive-stops]], [[OUT-2026-09-08-spec-adaptive-stops]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
