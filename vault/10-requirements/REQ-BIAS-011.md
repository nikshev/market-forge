---
id: REQ-BIAS-011
title: Store all discarded experiment variants to reduce silent cherry-picking.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5327-5327"
phase: null
status: specified
depends_on: []
tags: []
---

## Requirement

Store all discarded experiment variants to reduce silent cherry-picking.

## Acceptance

Store all discarded experiment variants to reduce silent cherry-picking.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-053-experiment-registry]]
- **Tests:**
    - `tests/unit/experiments/test_registry.py::test_a_discarded_variant_is_recorded_exactly_like_a_kept_one`
    - `tests/unit/experiments/test_registry.py::test_the_registry_is_append_only_and_its_history_does_not_change`
    - `tests/unit/experiments/test_report.py::test_a_field_of_one_is_a_legitimate_report`
    - `tests/unit/experiments/test_report.py::test_a_field_that_counts_a_variant_twice_is_refused`
    - `tests/unit/experiments/test_report.py::test_a_variant_that_lost_and_was_never_recorded_stops_the_report`
    - `tests/unit/experiments/test_report.py::test_a_winner_that_is_not_in_its_own_field_is_refused`
- **Code:**
    - `src/channelflow/experiments/__init__.py`
    - `src/channelflow/experiments/registry.py`
    - `src/channelflow/experiments/report.py`
- **Outcomes:** [[OUT-2026-09-09-implement-experiment-registry]], [[OUT-2026-09-09-plan-experiment-registry]], [[OUT-2026-09-09-requirement-experiment-registry]], [[OUT-2026-09-09-spec-experiment-registry]]
<!-- trace:end -->

## Notes

[[ADR-024]] recorded that this rule had no home: "experiment tracking, which
nothing here does". [[REQ-REPRO-001]] builds one — a registry on the canonical
plane that records every variant, kept or discarded, and a reporting gate that
refuses a winner whose field is not on record.

The status is `specified` rather than `implemented`, deliberately. The mechanism
exists and nothing publishes through it: none of the seventeen research modules
reports its field to the registry yet. Marking the rule implemented on the
strength of an unused gate would claim the coverage [[ADR-024]] refused to claim
for rule 2 on the strength of one engine's guard, and the same refusal applies
here. It moves when the experiments adopt it. See [[ADR-054]].

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
