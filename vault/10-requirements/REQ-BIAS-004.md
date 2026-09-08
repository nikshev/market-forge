---
id: REQ-BIAS-004
title: No using final daily high/low before daily close.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5320-5320"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No using final daily high/low before daily close.

## Acceptance

No using final daily high/low before daily close.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-015-pit-dataset]]
- **Tests:**
    - `tests/unit/dataset/test_join.py::test_a_feature_from_an_unfinalized_bar_is_refused`
- **Code:**
    - `src/channelflow/dataset/join.py`
    - `src/channelflow/dataset/leakage.py`
- **Outcomes:** [[OUT-2026-09-08-implement-pit-dataset]], [[OUT-2026-09-08-spec-pit-dataset]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
