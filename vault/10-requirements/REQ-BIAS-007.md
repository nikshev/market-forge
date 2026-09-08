---
id: REQ-BIAS-007
title: No survivor-only universe without point-in-time listing history.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5323-5323"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No survivor-only universe without point-in-time listing history.

## Acceptance

No survivor-only universe without point-in-time listing history.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-015-pit-dataset]]
- **Tests:**
    - `tests/unit/dataset/test_universe.py::test_a_delisted_symbol_is_absent_afterwards`
    - `tests/unit/dataset/test_universe.py::test_a_symbol_listed_later_is_absent_earlier`
- **Code:**
    - `src/channelflow/dataset/join.py`
- **Outcomes:** [[OUT-2026-09-08-implement-pit-dataset]], [[OUT-2026-09-08-spec-pit-dataset]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
