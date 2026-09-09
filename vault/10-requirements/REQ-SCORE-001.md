---
id: REQ-SCORE-001
title: Deterministic signal score, explainability and the alert ranker
type: work-package
prd_ref: "§22 Signal Scoring, §43 Alert Ranker"
prd_lines: "3952-3999, 5341-5359"
phase: null
status: implemented
depends_on: ["REQ-WP-007", "REQ-WP-011", "REQ-WP-012", "REQ-WP-013"]
tags: []
hard_gated: false
---

## Requirement

PRD §22.1, a deterministic score in `[0, 100]` over six feature groups, with the
PRD's own caps:

```text
channel_structure       0..30
rejection_quality       0..20
order_flow_confirmation 0..20
volume_confirmation     0..10
derivatives_context     0..10
defi_crossvenue_context 0..10
```

> "Missing family must not automatically equal zero; score should account for
> data availability with explicit confidence downgrade."

§22.2's worked example, which the arithmetic must reproduce:

```text
Channel structure        26/30
Rejection                17/20
Order flow               16/20
Volume                     7/10
Derivatives                8/10
DeFi/Cross venue           7/10
-------------------------------
Raw score                 81/100
Data quality multiplier   0.96
Final score               77.8
```

§22.3: the alert threshold is "configurable per symbol/timeframe/setup", and
`score >= 75` is a "default research value only".

§22.4, explainability — every signal stores:

- top positive factors;
- top negative factors;
- missing factors;
- raw feature snapshot;
- model/version used.

§43, the alert ranker:

```text
rank_score = setup_score * data_quality * liquidity_factor * novelty_factor
```

> - `data_quality` penalizes stale/missing sources;
> - `liquidity_factor` prevents noisy illiquid assets dominating;
> - `novelty_factor` reduces repeated correlated alerts.

## Acceptance

Deterministic score (§22.1, §22.2):

- each of the six groups contributes at most the cap the PRD gives it, and a
  contribution above its cap is refused rather than clipped silently;
- the raw score is the sum of the group contributions, and the final score is
  the raw score times the data quality multiplier;
- §22.2's worked example reproduces exactly: 81 raw, 0.96 multiplier, 77.8
  final;
- a missing family is recorded as missing and lowers the confidence, and is
  never scored as zero;
- a score computed twice over one input is the same score.

Threshold (§22.3):

- the alert threshold is configuration, defaulting to 75, and the default is
  labelled a research value;
- the threshold is resolvable per symbol, timeframe and setup type.

Explainability (§22.4):

- a scored signal carries its top positive factors, its top negative factors,
  its missing factors, the raw feature snapshot it was computed from, and the
  version of the scoring model used;
- the factors name the six PRD groups, so channel, order flow, volume,
  derivatives and DeFi/cross-venue are each visible as a contribution or as an
  explicit absence;
- an explanation cannot be produced for a score that was never computed.

Ranker (§43):

- `rank_score` is the product of setup score, data quality, liquidity factor and
  novelty factor;
- each factor is bounded to `[0, 1]` except the setup score, and a factor
  outside its range is refused;
- ranking is total and stable: two candidates with equal rank scores order by a
  declared tie-break rather than by input order.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-025-signal-scoring]]
- **Tests:**
    - `tests/unit/scoring/test_explain.py::test_a_missing_family_is_never_listed_among_the_negative_factors`
    - `tests/unit/scoring/test_explain.py::test_a_smaller_number_filling_more_of_its_cap_outranks_a_larger_one`
    - `tests/unit/scoring/test_explain.py::test_a_tie_is_broken_by_a_declared_key_not_by_input_order`
    - `tests/unit/scoring/test_explain.py::test_an_explanation_carries_all_five_of_section_22_4s_items`
    - `tests/unit/scoring/test_explain.py::test_an_explanation_needs_a_score`
    - `tests/unit/scoring/test_explain.py::test_every_group_appears_as_a_contribution_or_as_an_absence`
    - `tests/unit/scoring/test_explain.py::test_positive_and_negative_are_measured_against_each_groups_own_cap`
    - `tests/unit/scoring/test_explain.py::test_the_model_version_is_required`
    - `tests/unit/scoring/test_explain.py::test_the_tie_break_holds_for_a_score_built_by_hand`
    - `tests/unit/scoring/test_ranker.py::test_a_factor_outside_its_range_is_refused[data_quality]`
    - `tests/unit/scoring/test_ranker.py::test_a_factor_outside_its_range_is_refused[liquidity_factor]`
    - `tests/unit/scoring/test_ranker.py::test_a_factor_outside_its_range_is_refused[novelty_factor]`
    - `tests/unit/scoring/test_ranker.py::test_a_threshold_outside_the_score_range_is_refused`
    - `tests/unit/scoring/test_ranker.py::test_an_illiquid_asset_cannot_rank_on_setup_quality_alone`
    - `tests/unit/scoring/test_ranker.py::test_an_override_is_no_longer_a_research_default`
    - `tests/unit/scoring/test_ranker.py::test_ranking_is_stable_across_input_orders`
    - `tests/unit/scoring/test_ranker.py::test_ranking_orders_by_rank_score_descending`
    - `tests/unit/scoring/test_ranker.py::test_the_default_threshold_is_the_prds_research_value`
    - `tests/unit/scoring/test_ranker.py::test_the_most_specific_override_wins`
    - `tests/unit/scoring/test_ranker.py::test_the_rank_score_is_the_prds_product`
    - `tests/unit/scoring/test_ranker.py::test_the_scoring_package_consults_no_clock`
    - `tests/unit/scoring/test_score.py::test_a_contribution_above_its_cap_is_refused_not_clipped`
    - `tests/unit/scoring/test_score.py::test_a_data_quality_multiplier_outside_its_range_is_refused`
    - `tests/unit/scoring/test_score.py::test_a_missing_family_is_not_scored_as_zero`
    - `tests/unit/scoring/test_score.py::test_a_missing_family_lowers_the_confidence_by_its_own_cap`
    - `tests/unit/scoring/test_score.py::test_a_negative_contribution_is_refused`
    - `tests/unit/scoring/test_score.py::test_a_partial_score_is_normalized_over_what_was_observable`
    - `tests/unit/scoring/test_score.py::test_a_score_with_nothing_present_is_refused`
    - `tests/unit/scoring/test_score.py::test_the_prds_own_worked_example_reproduces_exactly`
    - `tests/unit/scoring/test_score.py::test_the_same_group_cannot_be_supplied_twice`
    - `tests/unit/scoring/test_score.py::test_the_same_input_scores_identically_twice`
    - `tests/unit/scoring/test_score.py::test_the_six_groups_and_their_caps_are_the_prds`
- **Code:**
    - `src/channelflow/scoring/__init__.py`
    - `src/channelflow/scoring/explain.py`
    - `src/channelflow/scoring/groups.py`
    - `src/channelflow/scoring/ranker.py`
    - `src/channelflow/scoring/score.py`
- **Outcomes:** [[OUT-2026-09-09-implement-signal-scoring]], [[OUT-2026-09-09-plan-signal-scoring]], [[OUT-2026-09-09-spec-signal-scoring]]
<!-- trace:end -->

## Notes

Extracted on 2026-09-09 because [[REQ-US-001]] ("markets sorted by setup score")
and [[REQ-US-004]] ("contribution factors are shown for a setup") both need a
score that no requirement covered. PRD §22 and §43 specify it in full — groups,
caps, a worked example, a threshold and a ranking formula — so nothing here is
derived; it is quoted.

[[ADR-016]] left the score to §43 when the dedupe policy needed one, and this is
that requirement.
