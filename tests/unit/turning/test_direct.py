"""The direct turning-point baseline (REQ-WP-019 criterion 4, PRD section 13A.13)."""

from __future__ import annotations

import pytest

from channelflow.dataset import Row, WalkForwardFolds
from channelflow.models import REQUIRED_BASELINES, ComparisonReport, Score
from channelflow.turning import (
    FeatureMissing,
    design_matrix,
    run_direct_baseline,
)
from channelflow.turning.direct import HORIZON_TARGETS, aggregate

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND


@pytest.mark.trace("REQ-WP-019")
def test_the_direct_baseline_reports_metrics_per_fold_and_in_aggregate(
    signal_rows: list[Row],
) -> None:
    """SC-001, FR-001, FR-002.

    REQ-WP-019's fourth acceptance criterion, in its own words: "direct baseline
    metrics exist". This is the test that says they do.
    """
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(signal_rows)

    result = run_direct_baseline(folds, target="MAX", feature_names=("slope", "curvature"))

    assert len(result.folds) == len(folds)
    assert all(report.rows_scored > 0 for report in result.folds)
    assert result.rows_scored == sum(report.rows_scored for report in result.folds)
    assert result.model_brier is not None
    assert result.base_rate_brier is not None


@pytest.mark.trace("REQ-WP-019")
def test_a_learnable_target_beats_the_base_rate(signal_rows: list[Row]) -> None:
    """SC-001.

    The control. Without it, "does not beat the base rate" below would be
    consistent with a baseline that never beats anything.
    """
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(signal_rows)

    result = run_direct_baseline(folds, target="MAX", feature_names=("slope", "curvature"))

    assert result.beats_base_rate
    assert result.model_brier < result.base_rate_brier


@pytest.mark.trace("REQ-WP-019")
def test_a_signal_free_target_reports_that_it_does_not_beat_the_base_rate(
    signal_free_rows: list[Row],
) -> None:
    """SC-002, FR-002.

    Constitution Principle IV, and the reason `ComparisonReport` exists: a Brier
    score on its own reads like a result. Against a base rate it reads like what
    it is.
    """
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(signal_free_rows)

    result = run_direct_baseline(folds, target="MAX", feature_names=("slope", "curvature"))

    assert not result.beats_base_rate
    assert "does not beat" in result.summary


@pytest.mark.trace("REQ-WP-019")
def test_a_row_missing_a_declared_feature_is_refused(signal_rows: list[Row]) -> None:
    """SC-003, FR-003.

    A missing feature defaulted to zero is a row that says "no momentum" when it
    means "we do not know". The model learns from it either way, and nothing
    downstream can tell the two apart.
    """
    with pytest.raises(FeatureMissing, match="depth"):
        design_matrix(signal_rows, target="MAX", feature_names=("slope", "depth"))


@pytest.mark.trace("REQ-WP-019")
def test_the_target_is_one_of_section_23_5as_three_classes(signal_rows: list[Row]) -> None:
    """FR-002.

    Section 23.5A's Target E is `P(local_max_within_H)`, `P(local_min_within_H)`
    and `P(no_turn_within_H)`. A target outside that set is a different
    experiment wearing this one's name.
    """
    assert HORIZON_TARGETS == ("MAX", "MIN", "NO_TURN")

    with pytest.raises(ValueError, match="target"):
        design_matrix(signal_rows, target="REVERSAL", feature_names=("slope",))  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-019")
def test_the_target_column_is_the_named_class_and_nothing_else(signal_rows: list[Row]) -> None:
    """FR-002."""
    _, y = design_matrix(signal_rows, target="MAX", feature_names=("slope",))

    expected = [1.0 if row.label.label_class == "MAX" else 0.0 for row in signal_rows]
    assert list(y) == expected


@pytest.mark.trace("REQ-WP-019")
def test_features_are_read_in_the_declared_order_not_the_dicts(signal_rows: list[Row]) -> None:
    """FR-003.

    A design matrix whose columns follow dictionary order changes meaning when a
    row is built differently, and every coefficient silently changes with it.
    """
    forward, _ = design_matrix(signal_rows, target="MAX", feature_names=("slope", "curvature"))
    reversed_, _ = design_matrix(signal_rows, target="MAX", feature_names=("curvature", "slope"))

    assert list(forward[:, 0]) == list(reversed_[:, 1])
    assert list(forward[:, 1]) == list(reversed_[:, 0])


@pytest.mark.trace("REQ-WP-019")
def test_no_fold_is_fitted_and_scored_on_the_same_row(signal_rows: list[Row]) -> None:
    """SC-001, FR-001.

    `compare` refuses overlapping splits, so a baseline that fitted on its own
    validation rows would raise here rather than report a flattering number.
    Asserted directly as well, because the property is the point of the fold.
    """
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(signal_rows)

    for fold in folds:
        train_times = {row.as_of_ns for row in fold.train}
        validate_times = {row.as_of_ns for row in fold.validate}
        assert not train_times & validate_times

    run_direct_baseline(folds, target="MAX", feature_names=("slope", "curvature"))


@pytest.mark.trace("REQ-WP-019")
def test_a_fold_whose_target_never_occurs_is_reported_not_scored(
    signal_rows: list[Row],
) -> None:
    """FR-002.

    A constant target makes every model perfect and the comparison meaningless.
    Recorded as an unscored fold rather than averaged into the aggregate, where
    it would raise the reported quality of a model that learned nothing.
    """
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(signal_rows)

    result = run_direct_baseline(folds, target="MIN", feature_names=("slope", "curvature"))

    assert result.folds == ()
    assert result.rows_scored == 0
    assert not result.beats_base_rate
    assert "no fold" in result.summary


@pytest.mark.trace("REQ-WP-019")
def test_the_aggregate_is_weighted_by_rows_not_by_fold_count() -> None:
    """FR-002.

    Walk-forward folds are not the same size, and the last ones carry the most
    rows. An unweighted mean lets a three-row fold's lucky score count as much
    as a thirty-row fold's -- and the small folds are the early ones, fitted on
    the least data.

    Two folds, 10 rows at 0.4 and 90 rows at 0.1: the weighted answer is 0.13,
    the unweighted one 0.25.
    """
    reports = [
        _report(model_brier=0.4, base_rate_brier=0.5, rows=10),
        _report(model_brier=0.1, base_rate_brier=0.5, rows=90),
    ]

    result = aggregate(reports, [])

    assert result.model_brier == pytest.approx(0.13)
    assert result.base_rate_brier == pytest.approx(0.5)
    assert result.rows_scored == 100


def _report(*, model_brier: float, base_rate_brier: float, rows: int) -> ComparisonReport:
    scores = {name: Score(name=name, brier=None, ran=False) for name in REQUIRED_BASELINES}
    scores["no_skill_base_rate"] = Score(name="no_skill_base_rate", brier=base_rate_brier, ran=True)
    return ComparisonReport(
        model=Score(name="logistic_regression", brier=model_brier, ran=True),
        baselines=tuple(scores[name] for name in REQUIRED_BASELINES),
        rows_scored=rows,
    )
