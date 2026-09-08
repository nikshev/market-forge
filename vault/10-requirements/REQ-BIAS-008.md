---
id: REQ-BIAS-008
title: No using current top-volume coin list for historical universe backtest without point-in-time universe reconstruction.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5324-5324"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No using current top-volume coin list for historical universe backtest without point-in-time universe reconstruction.

## Acceptance

No using current top-volume coin list for historical universe backtest without point-in-time universe reconstruction.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-015-pit-dataset]]
- **Tests:**
    - `tests/unit/dataset/test_universe.py::test_eligibility_uses_only_trailing_observations`
    - `tests/unit/dataset/test_universe.py::test_rows_outside_the_universe_are_dropped_and_counted`
- **Code:**
    - `src/channelflow/dataset/join.py`
- **Outcomes:** [[OUT-2026-09-08-implement-pit-dataset]], [[OUT-2026-09-08-spec-pit-dataset]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
