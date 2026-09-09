"""PRD section 23.8's calibration metrics, and section 25.5's by-bucket view.

# @trace: REQ-EXP-008

REQ-EXP-008 asks for four numbers beside the Brier score: calibration, PR-AUC,
expectancy by probability bucket, and feature stability across folds. Each
answers a question the Brier score cannot.

**Calibration** asks whether a 0.7 means seven times in ten. A model can be
sharp and badly calibrated -- ranking correctly while its numbers mean nothing --
and every downstream threshold reads those numbers as probabilities.

**PR-AUC** rather than ROC-AUC, because the targets here are imbalanced. ROC-AUC
on a 5% positive rate looks respectable for a model that never finds anything;
precision-recall does not.

**Expectancy by bucket** is where calibration meets money: the model's 0.8
bucket has to make more than its 0.5 bucket, or its confidence is decoration.

**Feature stability** asks whether the model used the same inputs on each fold.
One that reaches for a different feature every time has found the fold, not the
market.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from channelflow.backtest import CostModel, EconomicReport, economic_report
from channelflow.backtest.outcomes import Outcome, SignalOutcome


@dataclass(frozen=True)
class CalibrationBin:
    """One band of predicted probability, and what actually happened in it."""

    low: float
    high: float
    count: int
    mean_predicted: float
    observed_rate: float

    @property
    def gap(self) -> float:
        """Signed: positive means the model promised more than it delivered."""
        return self.mean_predicted - self.observed_rate


@dataclass(frozen=True)
class Calibration:
    """The reliability curve, and one number summarising it."""

    bins: tuple[CalibrationBin, ...]
    #: Expected calibration error: the count-weighted mean absolute gap.
    error: float


def calibration(predicted: np.ndarray, actual: np.ndarray, *, bins: int = 10) -> Calibration:
    """How close the predicted probabilities are to the observed rates.

    Empty bins are omitted rather than reported at zero: a band the model never
    predicted has no observed rate, and a zero there drags the summary toward a
    model that looks better calibrated for having been silent.
    """
    if len(predicted) != len(actual):
        raise ValueError("predicted and actual must be the same length")
    if len(predicted) == 0:
        raise ValueError("calibration over no predictions is not zero error")

    edges = np.linspace(0.0, 1.0, bins + 1)
    built: list[CalibrationBin] = []
    for low, high in zip(edges[:-1], edges[1:], strict=False):
        inside = (predicted >= low) & ((predicted < high) if high < 1.0 else (predicted <= high))
        if not inside.any():
            continue
        built.append(
            CalibrationBin(
                low=float(low),
                high=float(high),
                count=int(inside.sum()),
                mean_predicted=float(predicted[inside].mean()),
                observed_rate=float(actual[inside].mean()),
            )
        )

    total = sum(b.count for b in built)
    error = sum(b.count * abs(b.gap) for b in built) / total
    return Calibration(bins=tuple(built), error=error)


def pr_auc(predicted: np.ndarray, actual: np.ndarray) -> float | None:
    """Area under the precision-recall curve, by the trapezoid rule.

    `None` when nothing is positive: precision is undefined and an area of zero
    would read as a model that found nothing rather than a target that never
    happened.
    """
    positives = int(actual.sum())
    if positives == 0:
        return None

    order = np.argsort(-predicted, kind="stable")
    ranked = actual[order]
    true_positives = np.cumsum(ranked)
    predicted_positives = np.arange(1, len(ranked) + 1)

    precision = true_positives / predicted_positives
    recall = true_positives / positives
    # Prepend recall 0 at the first point's precision, so the curve starts where
    # the model does rather than at the origin.
    recall = np.concatenate(([0.0], recall))
    precision = np.concatenate(([precision[0]], precision))
    return float(np.trapezoid(precision, recall))


@dataclass(frozen=True)
class BucketExpectancy:
    """One probability band, and what the trades in it were worth."""

    low: float
    high: float
    count: int
    report: EconomicReport | None
    reason: str = ""


def expectancy_by_bucket(
    predicted: np.ndarray,
    outcomes: Sequence[SignalOutcome],
    *,
    costs: CostModel,
    risk_per_trade: float = 0.02,
    edges: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> tuple[BucketExpectancy, ...]:
    """What the model's confidence was worth, band by band.

    Where calibration meets money: a model whose 0.8 bucket does not out-earn
    its 0.5 bucket has confidence that means nothing, however well calibrated
    its probabilities look.
    """
    if len(predicted) != len(outcomes):
        raise ValueError("one probability per outcome")

    built: list[BucketExpectancy] = []
    for low, high in zip(edges[:-1], edges[1:], strict=False):
        inside = [
            outcome
            for probability, outcome in zip(predicted, outcomes, strict=True)
            if low <= probability < high or (high == edges[-1] and probability == high)
        ]
        resolved = [o for o in inside if o.outcome is not Outcome.AMBIGUOUS]
        if not resolved:
            built.append(
                BucketExpectancy(
                    low=float(low),
                    high=float(high),
                    count=len(inside),
                    report=None,
                    reason="no resolved outcome in this band",
                )
            )
            continue
        built.append(
            BucketExpectancy(
                low=float(low),
                high=float(high),
                count=len(inside),
                report=economic_report(inside, costs=costs, risk_per_trade=risk_per_trade),
            )
        )
    return tuple(built)


def feature_stability(selections: Sequence[Sequence[str]]) -> float | None:
    """How often the same features are chosen across folds.

    The mean share of each fold's selection that also appears in every other
    fold's -- one when every fold agrees, zero when no feature is chosen twice.
    A model reaching for different inputs on each fold has found the fold.

    `None` for fewer than two folds: stability across one fold is not a
    measurement.
    """
    if len(selections) < 2:
        return None
    sets = [set(s) for s in selections]
    shares: list[float] = []
    for index, chosen in enumerate(sets):
        if not chosen:
            shares.append(0.0)
            continue
        others = [s for position, s in enumerate(sets) if position != index]
        shared = {name for name in chosen if all(name in other for other in others)}
        shares.append(len(shared) / len(chosen))
    return sum(shares) / len(shares)
