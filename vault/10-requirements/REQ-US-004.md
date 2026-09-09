---
id: REQ-US-004
title: Explain setup
type: user-story
prd_ref: "US-004 — Explain setup"
prd_lines: "263-266"
phase: null
status: implemented
depends_on: ["REQ-SCORE-001", "REQ-API-001"]
tags: []
---

## Requirement

As a user, I want to see the contribution factors: channel, OFI, volume profile, derivatives, DeFi.

## Acceptance

- contribution factors are shown for a setup, covering channel, OFI, volume profile, derivatives, and DeFi.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-026-scored-markets]]
- **Tests:**
    - `tests/unit/api/test_scored_markets.py::test_a_missing_family_is_missing_and_not_a_negative_factor[in_memory]`
    - `tests/unit/api/test_scored_markets.py::test_a_missing_family_is_missing_and_not_a_negative_factor[lakehouse]`
    - `tests/unit/api/test_scored_markets.py::test_a_scored_signals_detail_carries_its_explanation[in_memory]`
    - `tests/unit/api/test_scored_markets.py::test_a_scored_signals_detail_carries_its_explanation[lakehouse]`
    - `tests/unit/api/test_scored_markets.py::test_an_unscored_signal_still_returns_its_detail[in_memory]`
    - `tests/unit/api/test_scored_markets.py::test_an_unscored_signal_still_returns_its_detail[lakehouse]`
    - `tests/unit/api/test_scored_markets.py::test_the_outcome_stays_separate_from_the_explanation[in_memory]`
    - `tests/unit/api/test_scored_markets.py::test_the_outcome_stays_separate_from_the_explanation[lakehouse]`
- **Code:**
    - `apps/web/src/Explanation.tsx`
    - `apps/web/src/__tests__/Explanation.test.tsx`
    - `src/channelflow/api/repositories.py`
    - `src/channelflow/api/routes.py`
    - `src/channelflow/api/schemas.py`
- **Outcomes:** [[OUT-2026-09-09-implement-scored-markets]], [[OUT-2026-09-09-plan-scored-markets]], [[OUT-2026-09-09-spec-scored-markets]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
