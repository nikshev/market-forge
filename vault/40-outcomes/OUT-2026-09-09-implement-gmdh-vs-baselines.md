---
id: OUT-2026-09-09-implement-gmdh-vs-baselines
step: implement
records: [REQ-EXP-008]
commit: null
---

## What was done

`channelflow.models.regularized`, `.boosting` and `.metrics`: PRD §23.6's
regularized logistic and gradient boosted trees, and EXP-008's four metrics
beside the Brier score. 19 tests, fourteen mutations, all caught.

## The poor tree ADR-029 warned about, written by accident

The first boosting implementation was a stump booster: one split per round, and
a `max_depth` field that nothing read. On an interaction target it scored a
Brier of 0.2379 against logistic regression's 0.2371 — no better, because a sum
of single-feature stumps is additive in the features and cannot represent an
interaction at all.

That is exactly [[ADR-029]]'s warning: "implementing them badly is worse than
not having them, because a GMDH model that beats a poor tree looks validated". A
GMDH result beating that baseline would have been beating something structurally
blind to what GMDH is for.

Real depth-two trees score 0.0246 on the same target. The default depth is two
because that is the shallowest that can hold an interaction, and a test asserts
the booster halves the linear model's Brier — which the stump version failed.

## The dead field was the tell

`max_depth` existed and did nothing. A field nobody reads is a claim the code
does not keep, and this one claimed exactly the property that mattered.

## What was decided

- **The elastic net's strengths are required arguments** ([[ADR-050]]), which is
  ADR-029's objection kept rather than argued with. A test reads the signature.
- **Empty calibration bands are omitted.** Scored at zero gap, a model that
  stayed silent looks better calibrated than one that spoke.
- **PR-AUC is absent when nothing is positive**, rather than zero: precision is
  undefined, and zero reads as a model that found nothing.
- **Stability counts only what every fold chose.** A feature that appeared in one
  other fold is not one the model kept reaching for — and the fixture that
  separates those two readings is three folds where every feature appears twice.

## Mutation results

Fourteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| Empty calibration bins are scored | `test_empty_bins_are_omitted_rather_than_scored_as_perfect` (+1) |
| The calibration gap is always zero | `test_an_overconfident_model_has_a_positive_gap` |
| Calibration over nothing is allowed | `test_calibration_over_nothing_is_refused` |
| PR-AUC returns zero with no positives | `test_pr_auc_is_absent_when_nothing_is_positive` |
| PR-AUC ignores the ranking | `test_pr_auc_punishes_what_roc_would_forgive` |
| A bucket with nothing resolved is scored | `test_a_bucket_with_nothing_resolved_reports_its_reason` (+1) |
| Stability over one fold returns one | `test_feature_stability_over_one_fold_is_absent` |
| Stability counts any overlap | `test_a_feature_shared_with_only_some_folds_is_not_stable` |
| The trees are stumps again | `test_the_boosted_baseline_finds_an_interaction_the_linear_ones_cannot` |
| A split that does not improve is taken | same |
| The minimum leaf size is ignored | `test_a_leaf_size_larger_than_the_data_leaves_the_tree_unsplit` |
| The elastic net skips soft-thresholding | `test_a_stronger_l1_penalty_zeroes_more_coefficients` |
| The penalty guard is dropped | `test_a_negative_penalty_is_refused` |
| The new baselines leave the report | two of REQ-WP-018's own tests |

## What is still open

- **Two of §23.6's six are still not run**, with their reasons in every report:
  the single decision tree, and LightGBM/XGBoost's dependency question.
- **These are baselines, not models.** [[ADR-050]] says so, and the
  implementations are textbook on purpose.
