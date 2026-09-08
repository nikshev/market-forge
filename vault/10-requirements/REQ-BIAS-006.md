---
id: REQ-BIAS-006
title: No using later corrected/reconstructed DEX state as if known earlier unless audit semantics explicitly allow it.
type: constraint
hard_gated: true
prd_ref: "§41"
prd_lines: "5322-5322"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

No using later corrected/reconstructed DEX state as if known earlier unless audit semantics explicitly allow it.

## Acceptance

No using later corrected/reconstructed DEX state as if known earlier unless audit semantics explicitly allow it.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-020-evm-connector]]
- **Tests:**
    - `tests/unit/chain/test_ledger.py::test_a_read_before_the_reorg_still_returns_the_record`
    - `tests/unit/chain/test_ledger.py::test_a_reorg_orphans_a_record_and_never_edits_it`
- **Code:**
    - `src/channelflow/chain/ledger.py`
- **Outcomes:** [[OUT-2026-09-08-implement-evm-connector]], [[OUT-2026-09-08-spec-evm-connector]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
