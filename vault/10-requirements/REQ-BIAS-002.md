---
id: REQ-BIAS-002
title: No centered moving filters in live features.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5318-5318"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No centered moving filters in live features.

## Acceptance

No centered moving filters in live features.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-058-live-causality]]
- **Tests:**
    - `tests/unit/extrema/test_live_causality.py::test_a_feature_that_is_not_point_in_time_safe_cannot_be_registered`
    - `tests/unit/extrema/test_live_causality.py::test_a_forbidden_helper_is_found_wherever_it_appears`
    - `tests/unit/extrema/test_live_causality.py::test_every_exemption_carries_a_reason`
    - `tests/unit/extrema/test_live_causality.py::test_every_exemption_names_a_module_that_exists`
    - `tests/unit/extrema/test_live_causality.py::test_every_registered_feature_is_point_in_time_safe`
    - `tests/unit/extrema/test_live_causality.py::test_no_live_module_reaches_for_a_centred_helper`
    - `tests/unit/extrema/test_live_causality.py::test_the_exemption_is_one_module_wide_and_not_one_package`
    - `tests/unit/extrema/test_live_causality.py::test_the_scan_covers_every_package_and_not_just_one`
- **Code:**
    - `src/channelflow/extrema/causality.py`
    - `src/channelflow/features/registry.py`
- **Outcomes:** [[OUT-2026-09-10-implement-live-causality]], [[OUT-2026-09-10-plan-live-causality]], [[OUT-2026-09-10-spec-live-causality]]
<!-- trace:end -->

## Notes

[[ADR-024]] gave this rule a home and refused to claim coverage for it "on the
strength of one engine's guard". The refusal was right for longer than it looked:
`require_causal` had one call site in the repository and it was inside a research
comparison, the forbidden-import scan read one package out of twenty-eight, and
every feature declared `point_in_time_safe=True` with no rule reading the field.

Two of the three are closed ([[SPEC-058-live-causality]]): every module under
`src/channelflow/` is scanned unless explicitly exempt, and an unsafe feature is
now unregisterable rather than registered and caught later.

The third is open and is the largest. `require_causal` still has no live call
site, because nothing computes live features from declared transforms yet. When
that path exists, the guard is what belongs at its entrance.

Both checks here are tripwires, not detectors — [[ADR-022]] settled that a
general detector is not achievable. Someone writing a centred moving average by
hand imports nothing and breaks the rule; Test A is the backstop for a transform
that lies about itself.

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
