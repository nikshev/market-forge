---
id: REQ-BIAS-003
title: No pivot that requires future bars unless the feature availability time is shifted to confirmation time.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5319-5319"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No pivot that requires future bars unless the feature availability time is shifted to confirmation time.

## Acceptance

No pivot that requires future bars unless the feature availability time is shifted to confirmation time.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-015-pit-dataset]]
- **Tests:**
    - `tests/unit/dataset/test_labels.py::test_a_label_cannot_claim_to_predate_its_extremum`
    - `tests/unit/dataset/test_labels.py::test_a_labels_availability_is_the_confirmation_time_not_the_extremum`
    - `tests/unit/dataset/test_leakage.py::test_a_label_available_before_its_extremum_is_caught`
- **Code:**
    - `src/channelflow/dataset/labels.py`
    - `src/channelflow/dataset/leakage.py`
- **Outcomes:** [[OUT-2026-09-08-implement-pit-dataset]], [[OUT-2026-09-08-spec-pit-dataset]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
