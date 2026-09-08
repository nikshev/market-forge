"""The comparison report PRD section 23.6 requires.

# @trace: REQ-WP-018

    "Every GMDH result must beat:
     - no-skill base rate;
     - logistic regression;
     - regularized logistic regression;
     - simple decision tree;
     - gradient boosted trees;
     - optionally LightGBM/XGBoost if dependency allowed."

Two of those six run here (ADR-029). The other four are named in every report
with a status, so a reader sees a partial comparison for what it is rather than
assuming the list was satisfied.

The report is the only place a GMDH score should ever be read from. A number
without its baselines is not a result -- Constitution Principle IV, and the
reason this whole layer waited for REQ-WP-019 and REQ-WP-017.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from channelflow.models.base import BaseRate, LogisticRegression, Model, require_disjoint

#: PRD section 23.6's list, verbatim and in order. Every report carries all six.
REQUIRED_BASELINES: tuple[str, ...] = (
    "no_skill_base_rate",
    "logistic_regression",
    "regularized_logistic_regression",
    "simple_decision_tree",
    "gradient_boosted_trees",
    "lightgbm_or_xgboost",
)

#: What ADR-029 leaves out, and why -- carried in the report rather than in a
#: comment, because the reader who needs it is not reading this file.
NOT_RUN = {
    "regularized_logistic_regression": (
        "not run: an L2 term with an unvalidated coefficient is not the baseline "
        "section 23.6 asks for"
    ),
    "simple_decision_tree": "not run: no tree implementation and no dependency (ADR-029)",
    "gradient_boosted_trees": "not run: no tree implementation and no dependency (ADR-029)",
    "lightgbm_or_xgboost": "not run: dependency not added (ADR-029)",
}


@dataclass(frozen=True)
class Score:
    name: str
    brier: float | None
    ran: bool
    note: str = ""


@dataclass(frozen=True)
class ComparisonReport:
    """One score per model, on identical data."""

    model: Score
    baselines: tuple[Score, ...]
    rows_scored: int

    @property
    def base_rate(self) -> Score:
        return next(b for b in self.baselines if b.name == "no_skill_base_rate")

    @property
    def beats_base_rate(self) -> bool:
        """Lower Brier is better. Ties do not count as beating it."""
        if self.model.brier is None or self.base_rate.brier is None:
            return False
        return self.model.brier < self.base_rate.brier

    @property
    def summary(self) -> str:
        """The sentence a reader takes away, including the bad one."""
        if not self.beats_base_rate:
            return (
                "the model does not beat the no-skill base rate; nothing here is evidence of skill"
            )
        unrun = [b.name for b in self.baselines if not b.ran]
        return (
            f"the model beats the base rate on {self.rows_scored} rows; "
            f"{len(unrun)} of PRD section 23.6's baselines were not run: "
            f"{', '.join(unrun)}"
        )


def brier(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Mean squared error of a probability against a binary outcome.

    PRD section 23.8 asks for it by name among the calibration metrics, and it
    is the right comparison here: accuracy would let a model that always
    predicts the majority class look strong on an imbalanced target -- which is
    exactly what the base-rate baseline exists to expose.
    """
    return float(np.mean((predicted - actual) ** 2))


def compare(
    model: Model,
    *,
    x_fit: np.ndarray,
    y_fit: np.ndarray,
    x_score: np.ndarray,
    y_score: np.ndarray,
    model_predictions: np.ndarray | None = None,
) -> ComparisonReport:
    """Score a model and its baselines on identical held-out data."""
    require_disjoint(x_fit, x_score)

    if model_predictions is None:
        model.fit(x_fit, y_fit)
        model_predictions = model.predict_proba(x_score)

    scores: list[Score] = []
    for baseline in (BaseRate(), LogisticRegression()):
        baseline.fit(x_fit, y_fit)
        scores.append(
            Score(
                name=baseline.name,
                brier=brier(baseline.predict_proba(x_score), y_score),
                ran=True,
            )
        )
    for name in REQUIRED_BASELINES:
        if any(s.name == name for s in scores):
            continue
        scores.append(Score(name=name, brier=None, ran=False, note=NOT_RUN[name]))

    return ComparisonReport(
        model=Score(name=model.name, brier=brier(model_predictions, y_score), ran=True),
        # Kept in the PRD's own order, so a reader comparing against section
        # 23.6 reads down the same list.
        baselines=tuple(next(s for s in scores if s.name == name) for name in REQUIRED_BASELINES),
        rows_scored=len(y_score),
    )
