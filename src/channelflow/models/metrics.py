"""PRD section 23.8's calibration metrics, and section 25.5's by-bucket view.

# @trace: REQ-EXP-008
# @trace: REQ-WP-023

REQ-EXP-008 asks for four numbers beside the Brier score: calibration, PR-AUC,
expectancy by probability bucket, and feature stability across folds. Each
answers a question the Brier score cannot.

PRD §23.5A conditions turning-point probabilities on an explicit horizon, so
[[REQ-WP-023]] adds a second reporter beside the first: the same curve, sliced
by the horizon each row's own label carries. A pooled figure averages across
horizons a forecast is never acted on together, and is dragged toward whichever
horizon supplied the most rows -- a fact about the dataset rather than about the
model.

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
from typing import Protocol

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


# --- calibration per horizon (REQ-WP-023) ------------------------------------
#
# PRD §23.5A conditions all three Target E classes on an explicit horizon, and
# a model's reliability is not constant across them: five bars ahead is nearly
# the present, fifty is a different question about a different market.
#
# Pooled, a model well calibrated at short horizons and badly at long ones
# reports an acceptable number, because the average is dragged toward whichever
# horizon supplied the most rows. That is a fact about the dataset rather than
# about the model, and the failure it hides is the one that matters: a forecast
# is acted on at one horizon, never at the average of several.


class LabelLike(Protocol):
    """What this reporter needs to read from a label, and nothing more.

    A protocol rather than an import, the way `dataset.leakage` does it: a
    metrics module that imported the dataset package would make the dependency
    run the wrong way, and this needs two fields out of a model with a dozen.
    """

    @property
    def label_class(self) -> str: ...

    @property
    def horizon_end_ns(self) -> int: ...


class RowWithLabel(Protocol):
    """A row that knows when it was taken and what it is a label about."""

    @property
    def as_of_ns(self) -> int: ...

    @property
    def label(self) -> LabelLike: ...


@dataclass(frozen=True)
class HorizonSlice:
    """One horizon's reliability, or the reason there is none."""

    horizon_ns: int
    observations: int
    #: `None` when the slice has too few rows to say anything. Absent and poor
    #: are different facts, and this is the third place in the repository that
    #: distinction has had to be made explicit.
    curve: Calibration | None
    reason: str = ""


@dataclass(frozen=True)
class HorizonCalibration:
    """Reliability per horizon, and the pooled figure beside it.

    Beside, never instead. Removing the pooled number breaks readers who have
    been quoting it; replacing the slices with it is the defect this exists to
    fix.
    """

    slices: dict[int, HorizonSlice]
    pooled: Calibration
    target: str


def calibration_by_horizon(
    rows: Sequence[RowWithLabel],
    predicted: np.ndarray,
    *,
    target: str,
    minimum_observations: int,
) -> HorizonCalibration:
    """Reliability for `target`, one curve per horizon the rows actually carry.

    The horizon is each row's own -- `horizon_end_ns` less `as_of_ns` -- rather
    than an argument, because a horizon supplied alongside the predictions is one
    a caller can get wrong with nothing to notice.

    Grouped exactly rather than bucketed: labels are built with a stated `H`, so
    rows share exact horizons, and bands would add a second arbitrary choice on
    top of `minimum_observations`.

    `minimum_observations` is the caller's (Principle X). PRD §23.8 gives no
    number, so a constant here would be a threshold nobody could change -- and
    the threshold decides which findings are visible.

    Empty input is refused by `calibration` below, not here. A guard here raised
    the same error with the same words one layer up, which is a rule stated twice
    and owned by neither -- the mutation sweep found it by deleting it and
    changing nothing.
    """
    if len(rows) != len(predicted):
        raise ValueError(
            f"{len(rows)} row(s) and {len(predicted)} prediction(s) must be the same "
            "length; a report over a misaligned pair is arithmetic on unrelated numbers"
        )
    actual = np.array(
        [1.0 if row.label.label_class == target else 0.0 for row in rows], dtype=np.float64
    )

    grouped: dict[int, list[int]] = {}
    for index, row in enumerate(rows):
        horizon = row.label.horizon_end_ns - row.as_of_ns
        grouped.setdefault(horizon, []).append(index)

    slices: dict[int, HorizonSlice] = {}
    for horizon in sorted(grouped):
        members = grouped[horizon]
        # On the row count, never on whether the target occurred. A target that
        # never occurred at a horizon has observations and no positives, which is
        # a real calibration and a bad one -- keying on positives would call it
        # unmeasured and hide the finding.
        if len(members) < minimum_observations:
            slices[horizon] = HorizonSlice(
                horizon_ns=horizon,
                observations=len(members),
                curve=None,
                reason=(
                    f"{len(members)} observation(s), fewer than the {minimum_observations} "
                    "this report was asked for; a curve over them would be the pooled "
                    "average speaking for a slice that cannot speak"
                ),
            )
            continue
        picked = np.array(members)
        slices[horizon] = HorizonSlice(
            horizon_ns=horizon,
            observations=len(members),
            curve=calibration(predicted[picked], actual[picked]),
        )

    return HorizonCalibration(slices=slices, pooled=calibration(predicted, actual), target=target)
