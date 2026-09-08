---
id: REQ-BIAS-010
title: Optimize parameters on train/validation; locked test remains untouched.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5326-5326"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Optimize parameters on train/validation; locked test remains untouched.

## Acceptance

Optimize parameters on train/validation; locked test remains untouched.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-015-pit-dataset]]
- **Tests:**
    - `tests/unit/dataset/test_folds.py::test_the_test_split_is_locked_until_explicitly_unlocked`
- **Code:**
    - `src/channelflow/dataset/folds.py`
- **Outcomes:** [[OUT-2026-09-08-implement-pit-dataset]], [[OUT-2026-09-08-spec-pit-dataset]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
