---
id: REQ-NRT-F
title: GMDH derivative root stability
type: constraint
hard_gated: true
prd_ref: "Test F — GMDH derivative root stability"
prd_lines: "2248-2251"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Small perturbations within a configured tolerance must not create silently unstable promoted roots. Record root sensitivity metrics.

## Acceptance

- small perturbations within a configured tolerance do not silently produce unstable promoted roots;
- root sensitivity metrics are recorded.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-024-turning-derivative]]
- **Tests:**
    - `tests/unit/turning/test_roots.py::test_a_negative_tolerance_is_refused`
    - `tests/unit/turning/test_roots.py::test_a_path_with_no_root_at_all_reports_zero_presence`
    - `tests/unit/turning/test_roots.py::test_a_root_that_only_some_members_find_is_refused_by_name`
    - `tests/unit/turning/test_roots.py::test_a_shallow_turn_is_refused_on_curvature`
    - `tests/unit/turning/test_roots.py::test_a_stable_root_survives_the_gate`
    - `tests/unit/turning/test_roots.py::test_an_excursion_inside_the_noise_floor_is_refused`
    - `tests/unit/turning/test_roots.py::test_disagreement_about_the_turn_type_is_measured`
    - `tests/unit/turning/test_roots.py::test_every_assessment_records_the_three_section_13a12_metrics`
    - `tests/unit/turning/test_roots.py::test_every_failing_condition_is_named_not_just_the_first`
    - `tests/unit/turning/test_roots.py::test_the_metrics_are_recorded_even_when_the_root_is_refused`
    - `tests/unit/turning/test_roots.py::test_the_same_path_and_tolerance_assess_identically_twice`
    - `tests/unit/turning/test_roots.py::test_the_thresholds_are_the_prds_research_defaults_and_are_configuration`
    - `tests/unit/turning/test_roots.py::test_the_turning_package_consults_neither_a_clock_nor_a_random_source`
- **Code:**
    - `src/channelflow/turning/roots.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-derivative]], [[OUT-2026-09-08-plan-turning-derivative]], [[OUT-2026-09-08-spec-turning-derivative]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
