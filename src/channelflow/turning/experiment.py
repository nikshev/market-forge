"""PRD section 13A.11's forward-path derivative experiment, end to end.

# @trace: REQ-WP-019

    "GMDH predicts a smooth forward conditional price path or return path over
     bounded horizon h in [0, H]."

One GMDH network per path coefficient, fitted on point-in-time features and
scored on a fold it never saw. Its predicted coefficients give a path per
validation row; the path gives roots; the roots face section 13A.12's gate; and
what survives becomes a prediction that is compared against the baselines
section 23.6 requires.

The experiment is allowed to conclude that there is nothing here. REQ-WP-019's
fifth acceptance criterion says so in as many words -- the derivative experiment
"can return `NO_EDGE` without blocking product completion" -- and [[ADR-042]] is
why that is a return value rather than an exception. A research result that
raises is a research result that blocks.

What still raises is a mistake in the call: a feature the rows do not carry, a
row with no forward path. Those are findings about the code, and reporting them
as `NO_EDGE` would dress them up as findings about the market.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from channelflow.dataset import Fold, Row
from channelflow.models import (
    ComparisonReport,
    GMDHNetwork,
    NotEnoughData,
    SplitOverlap,
    compare,
)
from channelflow.turning.direct import DirectBaselineResult, Target, aggregate, design_matrix
from channelflow.turning.path import PathCoefficients, RootCandidate, TurnType, derivative_roots
from channelflow.turning.roots import (
    PromotionDecision,
    PromotionGate,
    RootStability,
    assess_root_stability,
)

#: The four coefficients of section 13A.11's example polynomial path.
COEFFICIENTS: tuple[str, ...] = ("c0", "c1", "c2", "c3")

#: Where the training rows are cut into a fitting half and a selection half.
#: Chronological, and declared here rather than inside the search: ADR-030 has
#: `GMDHNetwork.fit` refuse to invent this split, because choosing it is exactly
#: what PRD section 41 rules 1 and 10 are about. The caller sees the rule.
DEFAULT_SELECTION_FRACTION = 0.5

#: Section 13A.12's perturbation tolerance for the stability assessment.
DEFAULT_TOLERANCE = 0.05


class Verdict(StrEnum):
    EDGE = "edge"
    NO_EDGE = "no_edge"


@dataclass
class _PredictionSource:
    """A name for the report. The predictions are supplied, so it never fits."""

    name: str = "gmdh_derivative_path"

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        raise NotEnoughData("the derivative experiment supplies its own predictions")

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        raise NotEnoughData("the derivative experiment supplies its own predictions")


@dataclass(frozen=True)
class ExperimentOutcome:
    """A verdict, and everything needed to disagree with it."""

    verdict: Verdict
    reason: str
    report: DirectBaselineResult | None = None
    stability: RootStability | None = None
    promoted: tuple[RootCandidate, ...] = ()
    rejected: tuple[PromotionDecision, ...] = ()
    #: Folds that could not be run, with why. Never silently dropped.
    unscored: tuple[str, ...] = field(default=())


def run_derivative_experiment(
    folds: list[Fold],
    *,
    feature_names: tuple[str, ...],
    path_targets: Mapping[int, PathCoefficients],
    target: Target,
    gate: PromotionGate | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
    selection_fraction: float = DEFAULT_SELECTION_FRACTION,
) -> ExperimentOutcome:
    """Run it, and say what happened -- including that nothing did."""
    gate = gate or PromotionGate()
    reports: list[ComparisonReport] = []
    promoted: list[RootCandidate] = []
    rejected: list[PromotionDecision] = []
    unscored: list[str] = []
    last_stability: RootStability | None = None

    for fold in folds:
        x_train, y_train = design_matrix(
            list(fold.train), target=target, feature_names=feature_names
        )
        x_validate, y_validate = design_matrix(
            list(fold.validate), target=target, feature_names=feature_names
        )
        cut = int(len(fold.train) * selection_fraction)
        if cut < 2 or len(fold.train) - cut < 2:
            unscored.append(
                f"fold {fold.index}: {len(fold.train)} training rows cannot make a "
                "fitting and a selection split of two rows each"
            )
            continue
        if len(np.unique(y_train)) < 2 or len(np.unique(y_validate)) < 2:
            unscored.append(
                f"fold {fold.index}: the target {target!r} is constant on one of its "
                "splits, so every model predicts it perfectly"
            )
            continue

        try:
            models = _fit_coefficient_models(
                x_train[:cut],
                x_train[cut:],
                _coefficient_targets(list(fold.train), path_targets),
                cut,
                feature_names,
            )
        except (NotEnoughData, SplitOverlap) as exc:
            unscored.append(f"fold {fold.index}: {exc}")
            continue

        horizon = _horizon(list(fold.train), path_targets)
        predictions = []
        for index in range(len(fold.validate)):
            path = _predicted_path(models, x_validate[index : index + 1], horizon)
            stability = assess_root_stability(path, tolerance=tolerance)
            last_stability = stability
            probability = 0.0
            for candidate in derivative_roots(path):
                decision = gate.assess(candidate, stability)
                if decision.promoted and candidate.turn_type is _wanted(target):
                    promoted.append(candidate)
                    # The presence rate is the experiment's own confidence: the
                    # share of perturbed members that still found this root. A
                    # promoted root nothing else agreed on predicts weakly,
                    # which is the honest reading.
                    probability = max(probability, stability.presence_rate)
                elif not decision.promoted:
                    rejected.append(decision)
            predictions.append(probability)

        try:
            reports.append(
                compare(
                    _PredictionSource(),
                    x_fit=x_train,
                    y_fit=y_train,
                    x_score=x_validate,
                    y_score=y_validate,
                    model_predictions=np.array(predictions, dtype=np.float64),
                )
            )
        except SplitOverlap as exc:
            unscored.append(f"fold {fold.index}: {exc}")

    if not reports:
        return ExperimentOutcome(
            verdict=Verdict.NO_EDGE,
            reason=f"no fold could be scored: {'; '.join(unscored) or 'no folds were given'}",
            stability=last_stability,
            promoted=tuple(promoted),
            rejected=tuple(rejected),
            unscored=tuple(unscored),
        )

    result = aggregate(reports, unscored)
    if not promoted:
        reason = (
            f"no derivative root survived section 13A.12's gate over "
            f"{result.rows_scored} scored row(s); {len(rejected)} were rejected"
        )
    elif not result.beats_base_rate:
        reason = (
            f"{len(promoted)} root(s) were promoted, but the predictions do not beat "
            f"the no-skill base rate: {result.summary}"
        )
    else:
        reason = f"{len(promoted)} promoted root(s); {result.summary}"

    return ExperimentOutcome(
        verdict=Verdict.EDGE if promoted and result.beats_base_rate else Verdict.NO_EDGE,
        reason=reason,
        report=result,
        stability=last_stability,
        promoted=tuple(promoted),
        rejected=tuple(rejected),
        unscored=tuple(unscored),
    )


def _wanted(target: Target) -> TurnType | None:
    """Which turn type this target is about. `NO_TURN` is about neither."""
    if target == "MAX":
        return TurnType.MAX
    if target == "MIN":
        return TurnType.MIN
    return None


def _coefficient_targets(
    rows: list[Row], path_targets: Mapping[int, PathCoefficients]
) -> dict[str, np.ndarray]:
    """The label-side coefficients, one column per term."""
    paths = [_path_for(row, path_targets) for row in rows]
    return {
        name: np.array([getattr(path, name) for path in paths], dtype=np.float64)
        for name in COEFFICIENTS
    }


def _path_for(row: Row, path_targets: Mapping[int, PathCoefficients]) -> PathCoefficients:
    try:
        return path_targets[row.as_of_ns]
    except KeyError as exc:
        raise KeyError(
            f"row at {row.as_of_ns} has no forward path to learn from; skipping it "
            "would shrink the experiment's evidence without saying so"
        ) from exc


def _horizon(rows: list[Row], path_targets: Mapping[int, PathCoefficients]) -> float:
    return _path_for(rows[0], path_targets).horizon


def _fit_coefficient_models(
    x_fit: np.ndarray,
    x_select: np.ndarray,
    targets: Mapping[str, np.ndarray],
    cut: int,
    feature_names: tuple[str, ...],
) -> dict[str, GMDHNetwork | float]:
    """One network per coefficient -- or the constant, when there is nothing to learn.

    A coefficient that never varies across the training rows is a statement
    about the path's shape, not an estimate. Fitting a network to reproduce a
    constant would report a search that found structure where there was none.
    """
    fitted: dict[str, GMDHNetwork | float] = {}
    for name in COEFFICIENTS:
        column = targets[name]
        y_fit, y_select = column[:cut], column[cut:]
        if len(np.unique(column)) < 2:
            fitted[name] = float(column[0])
            continue
        network = GMDHNetwork(name=f"path_{name}")
        network.fit_with_selection(x_fit, y_fit, x_select, y_select, input_names=feature_names)
        fitted[name] = network
    return fitted


def _predicted_path(
    models: Mapping[str, GMDHNetwork | float], x_row: np.ndarray, horizon: float
) -> PathCoefficients:
    values = {}
    for name in COEFFICIENTS:
        model = models[name]
        values[name] = model if isinstance(model, float) else float(model.predict(x_row)[0])
    return PathCoefficients(horizon=horizon, **values)
