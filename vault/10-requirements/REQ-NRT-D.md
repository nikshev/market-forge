---
id: REQ-NRT-D
title: centered filter prohibition
type: constraint
hard_gated: true
prd_ref: "Test D — centered filter prohibition"
prd_lines: "2240-2243"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Production feature path fails validation if a transform declares symmetric/centered future dependence.

## Acceptance

- the production feature path fails validation if any transform declares symmetric/centered future dependence.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Tests:**
    - `tests/unit/extrema/test_non_repainting.py::test_d_a_causal_transform_is_allowed`
    - `tests/unit/extrema/test_non_repainting.py::test_d_a_centered_transform_is_refused_by_the_production_path`
    - `tests/unit/extrema/test_non_repainting.py::test_d_research_paths_are_not_guarded`
    - `tests/unit/extrema/test_non_repainting.py::test_d_the_engine_imports_no_centered_helper`
- **Code:**
    - `src/channelflow/channels/kalman.py`
    - `src/channelflow/extrema/causality.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-points]], [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
