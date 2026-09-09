"""EXP-008's calibration, PR-AUC, bucket expectancy and stability (REQ-EXP-008)."""

from __future__ import annotations

import numpy as np
import pytest

from channelflow.backtest import CostModel
from channelflow.backtest.outcomes import Outcome, SignalOutcome
from channelflow.models import (
    ElasticNetLogistic,
    GradientBoostedTrees,
    LogisticRegression,
    brier,
    calibration,
    expectancy_by_bucket,
    feature_stability,
    pr_auc,
)

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def outcome(kind: Outcome, ret: float) -> SignalOutcome:
    return SignalOutcome(
        horizon_end_ns=0,
        first_target_time_ns=None,
        first_invalidation_time_ns=None,
        mfe_pct=0.0,
        mae_pct=0.0,
        return_h=ret,
        outcome=kind,
    )


@pytest.mark.trace("REQ-EXP-008")
def test_a_perfectly_calibrated_model_has_no_calibration_error() -> None:
    """A 0.7 that happens seven times in ten. The control for the measure."""
    predicted = np.array([0.7] * 100)
    actual = np.array([1.0] * 70 + [0.0] * 30)

    result = calibration(predicted, actual, bins=10)

    assert result.error == pytest.approx(0.0, abs=1e-9)


@pytest.mark.trace("REQ-EXP-008")
def test_an_overconfident_model_has_a_positive_gap() -> None:
    """A model can rank perfectly and still be badly calibrated, and every
    downstream threshold reads its numbers as probabilities."""
    predicted = np.array([0.9] * 100)
    actual = np.array([1.0] * 50 + [0.0] * 50)

    result = calibration(predicted, actual, bins=10)

    assert result.error == pytest.approx(0.4)
    assert result.bins[0].gap == pytest.approx(0.4)


@pytest.mark.trace("REQ-EXP-008")
def test_empty_bins_are_omitted_rather_than_scored_as_perfect() -> None:
    """A band the model never predicted has no observed rate. Counted at zero
    gap it would drag the summary toward a model that looks better calibrated
    for having been silent."""
    predicted = np.array([0.05] * 50)
    actual = np.array([0.0] * 50)

    result = calibration(predicted, actual, bins=10)

    assert len(result.bins) == 1
    assert result.bins[0].count == 50


@pytest.mark.trace("REQ-EXP-008")
def test_calibration_over_nothing_is_refused() -> None:
    """Zero error over no predictions is the best possible score for a model
    that never spoke."""
    with pytest.raises(ValueError, match="no predictions"):
        calibration(np.array([]), np.array([]))


@pytest.mark.trace("REQ-EXP-008")
def test_a_perfect_ranking_scores_one_on_pr_auc() -> None:
    """Every positive above every negative."""
    predicted = np.array([0.9, 0.8, 0.7, 0.2, 0.1])
    actual = np.array([1.0, 1.0, 1.0, 0.0, 0.0])

    assert pr_auc(predicted, actual) == pytest.approx(1.0)


@pytest.mark.trace("REQ-EXP-008")
def test_pr_auc_punishes_what_roc_would_forgive() -> None:
    """The reason EXP-008 asks for PR rather than ROC: on an imbalanced target,
    a model that ranks most negatives above the positives still looks
    respectable by ROC and does not here."""
    predicted = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95])
    actual = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    area = pr_auc(predicted, actual)

    assert area is not None
    assert area < 0.2


@pytest.mark.trace("REQ-EXP-008")
def test_pr_auc_is_absent_when_nothing_is_positive() -> None:
    """Precision is undefined, and an area of zero would read as a model that
    found nothing rather than a target that never happened."""
    assert pr_auc(np.array([0.5, 0.6]), np.array([0.0, 0.0])) is None


@pytest.mark.trace("REQ-EXP-008")
def test_expectancy_rises_with_the_models_confidence_when_it_should() -> None:
    """Where calibration meets money: a model whose high-confidence bucket does
    not out-earn its low-confidence one has confidence that means nothing."""
    predicted = np.array([0.1] * 20 + [0.9] * 20)
    outcomes = [outcome(Outcome.STOP, -0.02)] * 20 + [outcome(Outcome.TARGET, 0.05)] * 20

    buckets = expectancy_by_bucket(predicted, outcomes, costs=COSTS)

    low = next(b for b in buckets if b.low == 0.0)
    high = next(b for b in buckets if b.high == 1.0)
    assert low.report is not None and high.report is not None
    assert high.report.expectancy_r > low.report.expectancy_r


@pytest.mark.trace("REQ-EXP-008")
def test_a_bucket_with_nothing_resolved_reports_its_reason() -> None:
    """Absent is not zero, here as everywhere."""
    predicted = np.array([0.9] * 5)
    outcomes = [outcome(Outcome.AMBIGUOUS, 0.05)] * 5

    buckets = expectancy_by_bucket(predicted, outcomes, costs=COSTS)

    high = next(b for b in buckets if b.high == 1.0)
    assert high.count == 5
    assert high.report is None
    assert "no resolved outcome" in high.reason


@pytest.mark.trace("REQ-EXP-008")
def test_feature_stability_is_one_when_every_fold_agrees() -> None:
    """A model reaching for the same inputs on every fold has found something
    that outlives the fold."""
    assert feature_stability([["a", "b"], ["a", "b"], ["b", "a"]]) == pytest.approx(1.0)


@pytest.mark.trace("REQ-EXP-008")
def test_feature_stability_is_zero_when_no_feature_survives() -> None:
    """A different feature each time is a model that found the fold."""
    assert feature_stability([["a"], ["b"], ["c"]]) == pytest.approx(0.0)


@pytest.mark.trace("REQ-EXP-008")
def test_feature_stability_over_one_fold_is_absent() -> None:
    """Stability across one fold is not a measurement."""
    assert feature_stability([["a", "b"]]) is None


@pytest.mark.trace("REQ-EXP-008")
def test_the_boosted_baseline_finds_an_interaction_the_linear_ones_cannot() -> None:
    """PRD §23.6's reason for asking for a tree at all, and [[ADR-029]]'s
    warning made concrete: a booster of depth-one stumps is additive in the
    features and would have been a baseline that cannot see what GMDH is for.
    """
    rows = np.arange(200.0)
    x = np.column_stack([rows % 5, (rows % 7) - 3, np.sin(rows)])
    y = ((x[:, 0] > 2) ^ (x[:, 1] > 0)).astype(np.float64)

    trees = GradientBoostedTrees(trees=60)
    trees.fit(x, y)
    linear = LogisticRegression()
    linear.fit(x, y)

    assert brier(trees.predict_proba(x), y) < brier(linear.predict_proba(x), y) / 2


@pytest.mark.trace("REQ-EXP-008")
def test_the_elastic_net_requires_its_strengths() -> None:
    """[[ADR-029]]'s objection kept: "an L2 term with an unvalidated coefficient
    is not the baseline §23.6 asks for". A default would be that coefficient,
    chosen by this module and then invisible."""
    import inspect

    parameters = inspect.signature(ElasticNetLogistic).parameters

    assert parameters["penalty"].default is inspect.Parameter.empty
    assert parameters["l1_ratio"].default is inspect.Parameter.empty


@pytest.mark.trace("REQ-EXP-008")
def test_a_stronger_l1_penalty_zeroes_more_coefficients() -> None:
    """The point of the L1 term, and of the soft-thresholding step: a plain
    gradient leaves coefficients hovering near zero instead of at it."""
    rows = np.arange(200.0)
    x = np.column_stack([rows % 5, np.sin(rows), np.cos(rows), rows % 3])
    y = (x[:, 0] > 2).astype(np.float64)

    weak = ElasticNetLogistic(penalty=0.0001, l1_ratio=1.0)
    weak.fit(x, y)
    strong = ElasticNetLogistic(penalty=0.5, l1_ratio=1.0)
    strong.fit(x, y)

    assert np.count_nonzero(strong._weights) < np.count_nonzero(weak._weights)


@pytest.mark.trace("REQ-EXP-008")
def test_a_negative_penalty_is_refused() -> None:
    """It would reward large weights, which is not a penalty."""
    with pytest.raises(ValueError, match="magnitude"):
        ElasticNetLogistic(penalty=-1.0, l1_ratio=0.5)


@pytest.mark.trace("REQ-EXP-008")
def test_both_new_baselines_are_deterministic() -> None:
    """No seed anywhere: the splits are exhaustive and the descent is fixed."""
    rows = np.arange(120.0)
    x = np.column_stack([rows % 5, np.sin(rows)])
    y = (x[:, 0] > 2).astype(np.float64)

    def fitted(model):
        model.fit(x, y)
        return model.predict_proba(x)

    assert np.array_equal(
        fitted(GradientBoostedTrees(trees=20)), fitted(GradientBoostedTrees(trees=20))
    )
    assert np.array_equal(
        fitted(ElasticNetLogistic(penalty=0.01, l1_ratio=0.5)),
        fitted(ElasticNetLogistic(penalty=0.01, l1_ratio=0.5)),
    )


@pytest.mark.trace("REQ-EXP-008")
def test_a_feature_shared_with_only_some_folds_is_not_stable() -> None:
    """Stability means the model kept reaching for the same inputs, not that a
    feature turned up somewhere else at least once.

    Three folds, no feature in all of them: every feature appears twice and is
    missing once. Counting any overlap calls that perfect stability; counting
    every fold calls it none, which is what it is.
    """
    assert feature_stability([["a", "b"], ["b", "c"], ["a", "c"]]) == pytest.approx(0.0)


@pytest.mark.trace("REQ-EXP-008")
def test_a_leaf_size_larger_than_the_data_leaves_the_tree_unsplit() -> None:
    """The guard that stops the tree memorizing its fold.

    With a minimum larger than the sample, no split is legal and the ensemble
    predicts one number. Without the guard it splits down to single rows, and
    the baseline a GMDH result must beat becomes a lookup table of the training
    fold.
    """
    rows = np.arange(40.0)
    x = np.column_stack([rows % 5, np.sin(rows)])
    y = (x[:, 0] > 2).astype(np.float64)

    unsplittable = GradientBoostedTrees(trees=10, min_samples=len(x))
    unsplittable.fit(x, y)

    assert len(np.unique(unsplittable.predict_proba(x))) == 1
