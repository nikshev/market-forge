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
    - `tests/unit/channels/test_features.py::test_a_channel_with_no_width_has_no_position`
    - `tests/unit/channels/test_features.py::test_the_channel_features_are_registered`
    - `tests/unit/channels/test_features.py::test_the_features_read_the_snapshot_rather_than_recomputing_it`
    - `tests/unit/channels/test_features.py::test_the_position_is_zero_at_the_lower_boundary`
    - `tests/unit/channels/test_features.py::test_the_width_is_a_percentage_of_the_centre`
    - `tests/unit/features/test_registry.py::test_every_exposed_feature_is_registered`
    - `tests/unit/features/test_registry.py::test_no_required_field_is_blank`
- **Code:**
    - `src/channelflow/channels/features.py`
    - `src/channelflow/derivatives/registry_entries.py`
    - `src/channelflow/features/registry.py`
    - `src/channelflow/volume/shape.py`
- **Outcomes:** [[OUT-2026-09-08-implement-ofi-lob-features]], [[OUT-2026-09-08-plan-ofi-lob-features]], [[OUT-2026-09-08-spec-ofi-lob-features]], [[OUT-2026-09-08-tasks-ofi-lob-features]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
