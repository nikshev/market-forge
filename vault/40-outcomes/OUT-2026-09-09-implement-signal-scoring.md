---
id: OUT-2026-09-09-implement-signal-scoring
step: implement
records: [REQ-SCORE-001]
commit: null
---

## What was done

`channelflow.scoring`: PRD §22's deterministic score, §22.4's explanation and
§43's ranker. 32 tests, built around §22.2's own worked example.

## Two guards over one property, a fifth time

The sweep found two survivors, both in the explanation, and the second is the
recurring one.

**Ranking by raw contribution passed every test.** The fixture happened to order
the same way by value as by share of cap, so the property the code implements
was never distinguished from the one it does not. The case that separates them
is now a test: channel structure at 20 of 30 is the larger number, derivatives
at 9 of 10 is the stronger signal, and a panel ordered by raw value leads with
the channel group on every setup simply because its cap is the largest.

**The explanation's tie-break was hidden by `score_signal`'s sort.** Scores
arrive with their contributions already ordered, so removing the tie-break in
`explain` changed nothing — while any stored `SignalScore` reaching the panel by
another route would have ordered arbitrarily. The new test builds the score by
hand, in reverse, so only the explanation's own ordering can produce the answer.

## What was decided

- **A missing family leaves the denominator** ([[ADR-044]]), and the confidence
  carries §22.1's "explicit confidence downgrade". A family present and scoring
  zero is not listed as missing — that distinction is what the rule is for.
- **Factors rank by share of their own cap.** 26 of 30 and 8 of 10 are both
  strong; 4 of 20 is weak while being the larger number.
- **A missing family is never a negative factor.** "We have no DeFi data" and
  "the DeFi evidence is against this setup" are different statements, and §22.4
  gives them separate lists.
- **The 75 threshold travels with its label.** §22.3 calls it a "default research
  value only", and a resolved threshold says whether it is the PRD's placeholder
  or somebody's decision.

## Mutation results

Fifteen mutations, all caught, every restore verified and the tree swept
afterwards:

| Mutation | Caught by |
| --- | --- |
| An over-cap contribution is clipped | `test_a_contribution_above_its_cap_is_refused_not_clipped` |
| A negative contribution is accepted | `test_a_negative_contribution_is_refused` |
| A missing family scores zero | `test_a_missing_family_lowers_the_confidence_by_its_own_cap` (+1) |
| The duplicate-group check is dropped | `test_the_same_group_cannot_be_supplied_twice` |
| An empty score is allowed | `test_a_score_with_nothing_present_is_refused` |
| The data quality bound is dropped | `test_a_data_quality_multiplier_outside_its_range_is_refused` |
| Factors rank by raw value, not by share | `test_a_smaller_number_filling_more_of_its_cap_outranks_a_larger_one` |
| The explanation's tie-break is dropped | `test_the_tie_break_holds_for_a_score_built_by_hand` |
| A missing family is listed as a negative factor | `test_a_missing_family_is_never_listed_among_the_negative_factors` |
| An explanation needs no score | `test_an_explanation_needs_a_score` |
| A ranking factor above 1 is accepted | `test_a_factor_outside_its_range_is_refused` |
| The rank tie-break is dropped | `test_ranking_is_stable_across_input_orders` |
| Threshold resolution takes the least specific match | `test_the_most_specific_override_wins` |
| An out-of-range threshold is accepted | `test_a_threshold_outside_the_score_range_is_refused` |
| An override still reports the research default | `test_an_override_is_no_longer_a_research_default` |

## What is still open

- **Nothing consumes it yet.** [[REQ-US-001]] wants the market list sorted by it
  and [[REQ-US-004]] wants the explanation shown; both are next.
- **The data quality multiplier and the three ranking factors are supplied.**
  Computing them needs source freshness and liquidity this module does not hold.
