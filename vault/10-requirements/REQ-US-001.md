---
id: REQ-US-001
title: Scan markets
type: user-story
prd_ref: "US-001 — Scan markets"
prd_lines: "251-254"
phase: null
status: implemented
depends_on: ["REQ-SCORE-001", "REQ-API-001"]
tags: []
---

## Requirement

As a user, I want to see a list of markets, sorted by setup score, so that I can quickly find the most interesting situations.

## Acceptance

- the markets list is sorted by setup score.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-026-scored-markets]]
- **Tests:**
    - `tests/unit/api/test_scored_markets.py::test_a_filtered_list_is_still_ordered`
    - `tests/unit/api/test_scored_markets.py::test_a_market_carries_the_confidence_beside_its_score`
    - `tests/unit/api/test_scored_markets.py::test_an_unscored_market_sorts_last_with_null_scores`
    - `tests/unit/api/test_scored_markets.py::test_the_market_list_is_ordered_by_rank_score`
    - `tests/unit/api/test_scored_markets.py::test_the_order_is_the_same_twice`
    - `tests/unit/api/test_scored_markets.py::test_the_unscored_tail_is_ordered_by_name`
- **Code:**
    - `src/channelflow/api/ranking.py`
    - `src/channelflow/api/repositories.py`
    - `src/channelflow/api/routes.py`
    - `src/channelflow/api/schemas.py`
- **Outcomes:** [[OUT-2026-09-09-implement-scored-markets]], [[OUT-2026-09-09-plan-scored-markets]], [[OUT-2026-09-09-spec-scored-markets]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
