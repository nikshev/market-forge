---
id: REQ-NRT-B
title: candidate chronology
type: constraint
hard_gated: true
prd_ref: "Test B — candidate chronology"
prd_lines: "2228-2231"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

A candidate may be invalidated later, but its original snapshot cannot change.

## Acceptance

- a candidate's original snapshot never changes, even when the candidate is later invalidated.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Tests:**
    - `tests/unit/extrema/test_non_repainting.py::test_b_a_candidate_record_is_frozen`
    - `tests/unit/extrema/test_non_repainting.py::test_b_an_invalidated_candidate_keeps_its_original_record`
- **Code:**
    - `src/channelflow/extrema/models.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-points]], [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
