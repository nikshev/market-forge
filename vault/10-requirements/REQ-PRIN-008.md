---
id: REQ-PRIN-008
title: Every feature must have a description of its semantics, unit of measurement, cadence, source, freshness, and leakage policy.
type: constraint
hard_gated: false
prd_ref: "§0"
prd_lines: "22-22"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Every feature must have a description of its semantics, unit of measurement, cadence, source, freshness, and leakage policy.

## Acceptance

Every feature must have a description of its semantics, unit of measurement, cadence, source, freshness, and leakage policy.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-011-ofi-lob-features]]
- **Tests:**
    - `tests/unit/features/test_registry.py::test_every_exposed_feature_is_registered`
    - `tests/unit/features/test_registry.py::test_no_required_field_is_blank`
- **Code:**
    - `src/channelflow/derivatives/registry_entries.py`
    - `src/channelflow/features/registry.py`
    - `src/channelflow/volume/shape.py`
- **Outcomes:** [[OUT-2026-09-08-implement-ofi-lob-features]], [[OUT-2026-09-08-plan-ofi-lob-features]], [[OUT-2026-09-08-spec-ofi-lob-features]], [[OUT-2026-09-08-tasks-ofi-lob-features]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
