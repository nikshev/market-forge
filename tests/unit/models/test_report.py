"""PRD section 23.6's comparison report (REQ-WP-018).

    "Every GMDH result must beat: no-skill base rate; logistic regression;
     regularized logistic regression; simple decision tree; gradient boosted
     trees; optionally LightGBM/XGBoost if dependency allowed."

Two of six run here (ADR-029), and the report says so on its face.
"""

from __future__ import annotations

import numpy as np
import pytest

from channelflow.models import (
    REQUIRED_BASELINES,
    BaseRate,
    GMDHNetwork,
    LogisticRegression,
    SplitOverlap,
    brier,
    compare,
)


@pytest.mark.trace("REQ-WP-018")
def test_the_report_scores_the_model_and_baselines_on_identical_data(
    structured: tuple[np.ndarray, ...],
) -> None:
    """SC-006, FR-009. The comparison is only honest on one split."""
    x_fit, y_fit, x_score, y_score = structured

    report = compare(
        LogisticRegression(), x_fit=x_fit, y_fit=y_fit, x_score=x_score, y_score=y_score
    )

    assert report.rows_scored == len(y_score)
    assert report.model.brier is not None
    assert report.base_rate.brier is not None


@pytest.mark.trace("REQ-WP-018")
def test_every_baseline_from_the_prd_appears_in_the_report(
    structured: tuple[np.ndarray, ...],
) -> None:
    """SC-006, FR-011, ADR-029.

    All six, in the PRD's own order, so a reader comparing against §23.6 reads
    down the same list -- and sees the four that did not run rather than
    assuming the list was satisfied.
    """
    x_fit, y_fit, x_score, y_score = structured

    report = compare(BaseRate(), x_fit=x_fit, y_fit=y_fit, x_score=x_score, y_score=y_score)

    assert [b.name for b in report.baselines] == list(REQUIRED_BASELINES)
    ran = [b.name for b in report.baselines if b.ran]
    assert ran == ["no_skill_base_rate", "logistic_regression"]


@pytest.mark.trace("REQ-WP-018")
def test_unrun_baselines_carry_their_reason(
    structured: tuple[np.ndarray, ...],
) -> None:
    """FR-011. Carried in the report rather than in a comment, because the
    reader who needs it is not reading the source."""
    x_fit, y_fit, x_score, y_score = structured

    report = compare(BaseRate(), x_fit=x_fit, y_fit=y_fit, x_score=x_score, y_score=y_score)

    for baseline in report.baselines:
        if not baseline.ran:
            assert baseline.brier is None
            assert "not run" in baseline.note


@pytest.mark.trace("REQ-WP-018")
def test_a_model_that_does_not_beat_the_base_rate_is_reported_as_such(
    unstructured: tuple[np.ndarray, ...],
) -> None:
    """SC-007, FR-010.

    On noise the base rate is unbeatable by construction, and the summary must
    say the plain thing rather than reporting a number and leaving the reader
    to compare.
    """
    x_fit, y_fit, x_score, y_score = unstructured

    report = compare(
        LogisticRegression(), x_fit=x_fit, y_fit=y_fit, x_score=x_score, y_score=y_score
    )

    assert not report.beats_base_rate
    assert "does not beat" in report.summary
    assert "nothing here is evidence of skill" in report.summary


@pytest.mark.trace("REQ-WP-018")
def test_a_tie_with_the_base_rate_does_not_count_as_beating_it(
    structured: tuple[np.ndarray, ...],
) -> None:
    """FR-010. Comparing the base rate against itself is the exact tie, and
    "not worse" is not "better"."""
    x_fit, y_fit, x_score, y_score = structured

    report = compare(BaseRate(), x_fit=x_fit, y_fit=y_fit, x_score=x_score, y_score=y_score)

    assert report.model.brier == report.base_rate.brier
    assert not report.beats_base_rate


@pytest.mark.trace("REQ-WP-018")
def test_gmdh_beats_the_linear_baseline_on_an_interaction_target(
    structured: tuple[np.ndarray, ...],
) -> None:
    """The claim GMDH exists to make, tested rather than assumed.

    The target turns on `x0 * x1`, which no linear model can capture. If the
    quadratic nodes do not beat logistic regression here, the search is not
    doing its job -- and a fixture where both did equally well would prove
    nothing either way.
    """
    x_fit, y_fit, x_score, y_score = structured

    network = GMDHNetwork(max_layers=3)
    network.fit_with_selection(x_fit, y_fit, x_score, y_score)
    report = compare(
        network,
        x_fit=x_fit,
        y_fit=y_fit,
        x_score=x_score,
        y_score=y_score,
        model_predictions=network.predict_proba(x_score),
    )

    logistic = next(b for b in report.baselines if b.name == "logistic_regression")
    assert report.model.brier is not None and logistic.brier is not None
    assert report.model.brier < logistic.brier
    assert report.beats_base_rate


@pytest.mark.trace("REQ-WP-018")
def test_the_report_refuses_overlapping_splits(
    structured: tuple[np.ndarray, ...],
) -> None:
    """FR-002 again, at the reporting boundary: a report computed on training
    rows is the most flattering number in the system."""
    x_fit, y_fit, _, _ = structured

    with pytest.raises(SplitOverlap):
        compare(BaseRate(), x_fit=x_fit, y_fit=y_fit, x_score=x_fit, y_score=y_fit)


@pytest.mark.trace("REQ-WP-018")
def test_brier_rewards_calibration_not_confidence() -> None:
    """PRD section 23.8 names Brier among the calibration metrics.

    Accuracy would let a model that always predicts the majority class look
    strong on an imbalanced target, which is exactly what the base-rate
    baseline exists to expose.
    """
    actual = np.array([1.0, 1.0, 1.0, 0.0])

    confident_and_wrong = brier(np.array([1.0, 1.0, 1.0, 1.0]), actual)
    honest = brier(np.array([0.75, 0.75, 0.75, 0.75]), actual)

    assert honest < confident_and_wrong
