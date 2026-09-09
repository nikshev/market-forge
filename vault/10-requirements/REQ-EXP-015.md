---
id: REQ-EXP-015
title: Derivatives/DeFi confluence at turning points
type: experiment
prd_ref: "EXP-015 Derivatives/DeFi confluence at turning points"
prd_lines: "5229-5240"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

For BTC/ETH and other liquid assets, test whether turning-point probability improves from:

- OI/funding/liquidations;
- DEX-CEX executable basis;
- DEX depth asymmetry;
- swap imbalance;
- LP liquidity migration.

Use strict ablation and same walk-forward folds.

## Acceptance

- the ablation is strict and uses the same walk-forward folds across OI/funding/liquidations, DEX-CEX executable basis, DEX depth asymmetry, swap imbalance, and LP liquidity migration variants.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-048-defi-confluence]]
- **Tests:**
    - `tests/unit/research/test_defi_confluence.py::test_a_family_is_measured_both_alone_and_in_context`
    - `tests/unit/research/test_defi_confluence.py::test_a_family_that_helps_both_ways_is_named_as_such`
    - `tests/unit/research/test_defi_confluence.py::test_a_family_that_helps_neither_way_is_named_as_such`
    - `tests/unit/research/test_defi_confluence.py::test_a_family_with_no_features_is_unmeasured_rather_than_worthless`
    - `tests/unit/research/test_defi_confluence.py::test_an_arm_two_families_from_both_references_is_refused`
    - `tests/unit/research/test_defi_confluence.py::test_every_arm_is_one_family_from_a_reference`
    - `tests/unit/research/test_defi_confluence.py::test_every_arm_is_scored_on_one_fold_set`
    - `tests/unit/research/test_defi_confluence.py::test_reports_on_different_folds_cannot_be_compared`
    - `tests/unit/research/test_defi_confluence.py::test_the_dex_basis_family_does_not_claim_the_cex_perp_basis`
    - `tests/unit/research/test_defi_confluence.py::test_the_fingerprint_tells_apart_fold_sets_of_the_same_size`
    - `tests/unit/research/test_defi_confluence.py::test_the_five_families_the_prd_names_are_ablated`
    - `tests/unit/research/test_defi_confluence.py::test_the_improvement_floor_decides_what_counts_as_an_improvement`
    - `tests/unit/research/test_defi_confluence.py::test_the_improvement_floor_is_required_and_positive`
    - `tests/unit/research/test_defi_confluence.py::test_the_instruments_are_required_and_checked_against_the_data`
    - `tests/unit/research/test_defi_confluence.py::test_two_runs_produce_equal_reports`
- **Code:**
    - `src/channelflow/research/__init__.py`
    - `src/channelflow/research/defi_confluence.py`
- **Outcomes:** [[OUT-2026-09-09-implement-defi-confluence]], [[OUT-2026-09-09-plan-defi-confluence]], [[OUT-2026-09-09-spec-defi-confluence]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
