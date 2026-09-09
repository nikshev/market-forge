---
id: REQ-EXP-008
title: GMDH vs baselines
type: experiment
prd_ref: "EXP-008 GMDH vs baselines"
prd_lines: "5127-5145"
phase: null
status: implemented
depends_on: ["REQ-WP-018", "REQ-BT-001"]
tags: []
---

## Requirement

Same point-in-time feature matrix.

Models:

- logistic;
- elastic net;
- gradient boosting;
- GMDH.

Evaluate:

- Brier;
- calibration;
- PR-AUC;
- expectancy by probability bucket;
- feature stability across walk-forward folds.

## Acceptance

- logistic, elastic net, gradient boosting, and GMDH are evaluated on the same point-in-time feature matrix;
- Brier score is reported;
- calibration is reported;
- PR-AUC is reported;
- expectancy by probability bucket is reported;
- feature stability across walk-forward folds is reported.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-041-gmdh-vs-baselines]]
- **Tests:**
    - `tests/unit/models/test_metrics.py::test_a_bucket_with_nothing_resolved_reports_its_reason`
    - `tests/unit/models/test_metrics.py::test_a_feature_shared_with_only_some_folds_is_not_stable`
    - `tests/unit/models/test_metrics.py::test_a_leaf_size_larger_than_the_data_leaves_the_tree_unsplit`
    - `tests/unit/models/test_metrics.py::test_a_negative_penalty_is_refused`
    - `tests/unit/models/test_metrics.py::test_a_perfect_ranking_scores_one_on_pr_auc`
    - `tests/unit/models/test_metrics.py::test_a_perfectly_calibrated_model_has_no_calibration_error`
    - `tests/unit/models/test_metrics.py::test_a_stronger_l1_penalty_zeroes_more_coefficients`
    - `tests/unit/models/test_metrics.py::test_an_overconfident_model_has_a_positive_gap`
    - `tests/unit/models/test_metrics.py::test_both_new_baselines_are_deterministic`
    - `tests/unit/models/test_metrics.py::test_calibration_over_nothing_is_refused`
    - `tests/unit/models/test_metrics.py::test_empty_bins_are_omitted_rather_than_scored_as_perfect`
    - `tests/unit/models/test_metrics.py::test_expectancy_rises_with_the_models_confidence_when_it_should`
    - `tests/unit/models/test_metrics.py::test_feature_stability_is_one_when_every_fold_agrees`
    - `tests/unit/models/test_metrics.py::test_feature_stability_is_zero_when_no_feature_survives`
    - `tests/unit/models/test_metrics.py::test_feature_stability_over_one_fold_is_absent`
    - `tests/unit/models/test_metrics.py::test_pr_auc_is_absent_when_nothing_is_positive`
    - `tests/unit/models/test_metrics.py::test_pr_auc_punishes_what_roc_would_forgive`
    - `tests/unit/models/test_metrics.py::test_the_boosted_baseline_finds_an_interaction_the_linear_ones_cannot`
    - `tests/unit/models/test_metrics.py::test_the_elastic_net_requires_its_strengths`
- **Code:**
    - `src/channelflow/models/__init__.py`
    - `src/channelflow/models/boosting.py`
    - `src/channelflow/models/metrics.py`
    - `src/channelflow/models/regularized.py`
    - `src/channelflow/models/report.py`
- **Outcomes:** [[OUT-2026-09-09-implement-gmdh-vs-baselines]], [[OUT-2026-09-09-plan-gmdh-vs-baselines]], [[OUT-2026-09-09-spec-gmdh-vs-baselines]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
