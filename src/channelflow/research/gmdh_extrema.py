"""EXP-013: whether the derivative route to an extremum earns its complexity.

# @trace: REQ-EXP-013

    Compare: direct classifier only; GMDH direct turning-point classifier; GMDH
    forward path + derivative roots; ensemble of direct probability + derivative
    root stability.

    Report: root presence rate; root horizon IQR; turn-type agreement;
    time-to-turn MAE; extreme-price error; calibration; incremental expectancy
    after costs.

    Reject the derivative method if roots are unstable or add no OOS value.

Four arms, one set of folds, one design matrix. The derivative route is the
expensive one -- four networks per fold instead of one, a promotion gate, a
perturbation lattice -- and the only reason to pay for it is that it answers
questions a classifier cannot: *when* the turn comes and *at what price*.

So this module reports those two errors for the arms that make such a claim and
leaves them absent for the arms that do not. A classifier has no time-to-turn
error because it never named a time. Filling that in with a horizon borrowed
from elsewhere would let the cheap arm be judged on a promise it never made.

The verdict is the PRD's own last sentence, made mechanical: unstable roots or
no incremental value after costs, and the derivative method is rejected.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from channelflow.backtest import CostModel, NothingResolved, SignalOutcome, economic_report
from channelflow.dataset import CertifiedDataset, Row
from channelflow.models import (
    Calibration,
    ComparisonReport,
    GMDHNetwork,
    LogisticRegression,
    NotEnoughData,
    SplitOverlap,
    calibration,
    compare,
)
from channelflow.turning import (
    DirectBaselineResult,
    PathCoefficients,
    PromotionGate,
    RootCandidate,
    Verdict,
    read_derivative_folds,
    wanted_turn_type,
)
from channelflow.turning.direct import Target, aggregate
from channelflow.turning.experiment import (
    DEFAULT_SELECTION_FRACTION,
    DEFAULT_TOLERANCE,
    FoldReading,
)
from channelflow.turning.path import derivative_roots

#: EXP-013's four arms, in the PRD's order.
ARMS: tuple[str, ...] = (
    "direct_only",
    "gmdh_direct",
    "derivative_roots",
    "ensemble",
)

#: The arms whose output is a probability and nothing else. They are not worse
#: for it -- they are cheaper -- but they cannot be scored on a time or a price.
CLASSIFIER_ARMS: tuple[str, ...] = ("direct_only", "gmdh_direct")

#: The arm every other arm's incremental expectancy is measured against.
BASELINE_ARM = "direct_only"


class OutcomeMissing(LookupError):
    """A scored row has no recorded outcome to price."""


@dataclass(frozen=True)
class RootMetrics:
    """Section 13A.12's three stability figures, over the rows that had a root.

    All three are averaged over `rows_with_a_root`, never over every scored row.
    The presence rate is a property of a root -- the share of perturbed members
    that still found it -- so averaging it over rows whose path never turned
    measures how often the market turns, not how stable a turn is. On a fixture
    where half the paths run straight that alone drags the mean to 0.50 and
    fails the gate, which would read as "the roots are unstable" when the roots
    that exist are perfectly stable.

    Both counts are reported, so the share of rows that turned is still
    recoverable -- it is simply not the same number.
    """

    rows: int
    rows_with_a_root: int
    presence_rate: float | None
    horizon_iqr: float | None
    turn_type_agreement: float | None


@dataclass(frozen=True)
class ForecastError:
    """How far off the arm's *when* and *at what price* were.

    Both are absent for an arm that never named either. That absence is the
    finding EXP-013 is looking for -- it is what the derivative route costs its
    complexity to buy.
    """

    compared: int
    #: Rows the arm called where the true forward path never turned, so there is
    #: no time and no price to be wrong about. Counted, never averaged in.
    without_truth: int
    #: Rows the arm called without promoting a root of its own. The ensemble can
    #: cross the threshold on its classifier half alone, and a call with no root
    #: behind it names no time and no price -- so it is counted here rather than
    #: quietly leaving the denominator.
    called_without_a_root: int
    time_to_turn_mae: float | None
    extreme_price_error: float | None


@dataclass(frozen=True)
class ArmReport:
    """One arm, and every number EXP-013 asks for."""

    arm: str
    scored: DirectBaselineResult
    calibration: Calibration | None
    calls: int
    expectancy_r: float | None
    #: Against `BASELINE_ARM`, after costs. `None` for the baseline itself and
    #: for an arm whose calls could not be priced.
    incremental_expectancy_r: float | None
    roots: RootMetrics | None
    forecast: ForecastError | None
    #: Why an economic figure is missing, when it is. Never an empty string
    #: standing in for a number.
    unpriced: str | None = None

    @property
    def beats_base_rate(self) -> bool:
        return self.scored.beats_base_rate


@dataclass(frozen=True)
class ExtremaComparison:
    """The four arms, and the PRD's verdict on the derivative route."""

    arms: dict[str, ArmReport]
    verdict: Verdict
    reason: str
    gate: PromotionGate
    call_threshold: float
    unscored: tuple[str, ...]


def compare_gmdh_extrema(
    dataset: CertifiedDataset,
    *,
    feature_names: tuple[str, ...],
    path_targets: Mapping[int, PathCoefficients],
    target: Target,
    outcomes: Mapping[int, SignalOutcome],
    costs: CostModel,
    risk_per_trade: float,
    call_threshold: float,
    gate: PromotionGate | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
    selection_fraction: float = DEFAULT_SELECTION_FRACTION,
    calibration_bins: int = 10,
) -> ExtremaComparison:
    """Run EXP-013's four arms over one set of folds and rule on the derivative.

    `call_threshold` has no default. It decides which rows an arm is judged on,
    and every economic figure below moves with it -- PRD section 13A.27's
    warning about research defaults applies to it exactly.
    """
    if not 0.0 < call_threshold <= 1.0:
        raise ValueError(
            f"call_threshold {call_threshold} is outside (0, 1]; a threshold of zero "
            "calls every row and an arm that calls everything has no precision to "
            "measure"
        )
    gate = gate or PromotionGate()
    readings = read_derivative_folds(
        dataset,
        feature_names=feature_names,
        path_targets=path_targets,
        target=target,
        gate=gate,
        tolerance=tolerance,
        selection_fraction=selection_fraction,
    )
    validate_rows = {fold.index: list(fold.validate) for fold in dataset.folds}

    reports: dict[str, list[ComparisonReport]] = {arm: [] for arm in ARMS}
    predicted: dict[str, list[float]] = {arm: [] for arm in ARMS}
    actual: dict[str, list[float]] = {arm: [] for arm in ARMS}
    called: dict[str, list[Row]] = {arm: [] for arm in ARMS}
    promoted: dict[str, list[tuple[Row, RootCandidate | None]]] = {arm: [] for arm in ARMS}
    unscored = list(readings.unscored)

    for fold in readings.folds:
        rows = validate_rows[fold.index]
        try:
            probabilities = _arm_probabilities(fold, selection_fraction)
        except (NotEnoughData, SplitOverlap) as exc:
            unscored.append(f"fold {fold.index}: {exc}")
            continue

        for arm in ARMS:
            column = probabilities[arm]
            try:
                reports[arm].append(
                    compare(
                        _Named(arm),
                        x_fit=fold.x_train,
                        y_fit=fold.y_train,
                        x_score=fold.x_validate,
                        y_score=fold.y_validate,
                        model_predictions=column,
                    )
                )
            except SplitOverlap as exc:
                unscored.append(f"fold {fold.index}, arm {arm}: {exc}")
                continue
            predicted[arm].extend(float(p) for p in column)
            actual[arm].extend(float(y) for y in fold.y_validate)
            for index, row in enumerate(rows):
                if column[index] < call_threshold:
                    continue
                called[arm].append(row)
                if arm in CLASSIFIER_ARMS:
                    continue
                roots = fold.rows[index].promoted
                if not roots:
                    promoted[arm].append((row, None))
                for candidate in roots:
                    promoted[arm].append((row, candidate))

    root_metrics = _root_metrics(readings.folds)
    built: dict[str, ArmReport] = {}
    for arm in ARMS:
        economics, unpriced = _economics(
            called[arm], outcomes=outcomes, costs=costs, risk_per_trade=risk_per_trade
        )
        built[arm] = ArmReport(
            arm=arm,
            scored=aggregate(reports[arm], unscored),
            calibration=(
                calibration(
                    np.array(predicted[arm], dtype=np.float64),
                    np.array(actual[arm], dtype=np.float64),
                    bins=calibration_bins,
                )
                if predicted[arm]
                else None
            ),
            calls=len(called[arm]),
            expectancy_r=economics,
            incremental_expectancy_r=None,
            roots=None if arm in CLASSIFIER_ARMS else root_metrics,
            forecast=(
                None
                if arm in CLASSIFIER_ARMS
                else _forecast_error(promoted[arm], path_targets=path_targets, target=target)
            ),
            unpriced=unpriced,
        )

    built = _with_increments(built)
    verdict, reason = _rule(built, gate=gate)
    return ExtremaComparison(
        arms=built,
        verdict=verdict,
        reason=reason,
        gate=gate,
        call_threshold=call_threshold,
        unscored=tuple(unscored),
    )


@dataclass
class _Named:
    """A name for the report. Every arm supplies its own predictions."""

    name: str

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        raise NotEnoughData("EXP-013's arms supply their own predictions")

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        raise NotEnoughData("EXP-013's arms supply their own predictions")


def _arm_probabilities(fold: FoldReading, selection_fraction: float) -> dict[str, np.ndarray]:
    """Each arm's probability for every validation row in this fold."""
    direct = LogisticRegression()
    direct.fit(fold.x_train, fold.y_train)
    direct_probabilities = direct.predict_proba(fold.x_validate)

    cut = int(len(fold.x_train) * selection_fraction)
    network = GMDHNetwork(name="gmdh_direct")
    network.fit_with_selection(
        fold.x_train[:cut],
        fold.y_train[:cut],
        fold.x_train[cut:],
        fold.y_train[cut:],
    )
    gmdh_probabilities = network.predict_proba(fold.x_validate)

    roots = fold.probabilities
    return {
        "direct_only": direct_probabilities,
        "gmdh_direct": gmdh_probabilities,
        "derivative_roots": roots,
        # The mean, not the product. A product is zero wherever no root was
        # promoted, which would make the ensemble silent on exactly the rows
        # where the direct classifier is the only thing speaking -- an ensemble
        # that discards one of its two members is one member.
        "ensemble": (direct_probabilities + roots) / 2.0,
    }


def _root_metrics(folds: Sequence[FoldReading]) -> RootMetrics:
    """The three stability figures, averaged over every row that was read."""
    stabilities = [row.stability for fold in folds for row in fold.rows]
    if not stabilities:
        return RootMetrics(
            rows=0,
            rows_with_a_root=0,
            presence_rate=None,
            horizon_iqr=None,
            turn_type_agreement=None,
        )
    with_a_root = [s for s in stabilities if s.presence_rate > 0.0]
    return RootMetrics(
        rows=len(stabilities),
        rows_with_a_root=len(with_a_root),
        presence_rate=(
            sum(s.presence_rate for s in with_a_root) / len(with_a_root) if with_a_root else None
        ),
        horizon_iqr=(
            sum(s.horizon_iqr for s in with_a_root) / len(with_a_root) if with_a_root else None
        ),
        turn_type_agreement=(
            sum(s.turn_type_agreement for s in with_a_root) / len(with_a_root)
            if with_a_root
            else None
        ),
    )


def _forecast_error(
    calls: Sequence[tuple[Row, RootCandidate | None]],
    *,
    path_targets: Mapping[int, PathCoefficients],
    target: Target,
) -> ForecastError:
    """Time-to-turn MAE and extreme-price error against the true forward path.

    The truth is the label-side path itself: where *it* turns is when the turn
    came, and what it reads there is the extreme price. A row whose true path
    never turns has no answer, and is counted rather than scored as a miss --
    an arm is not wrong about a time that does not exist.
    """
    wanted = wanted_turn_type(target)
    time_errors: list[float] = []
    price_errors: list[float] = []
    without_truth = 0
    without_a_root = 0

    for row, candidate in calls:
        if candidate is None:
            without_a_root += 1
            continue
        truth = path_targets.get(row.as_of_ns)
        actual_root = None
        if truth is not None:
            actual_root = next((r for r in derivative_roots(truth) if r.turn_type is wanted), None)
        if actual_root is None:
            without_truth += 1
            continue
        time_errors.append(abs(candidate.horizon - actual_root.horizon))
        price_errors.append(abs(candidate.predicted_price - actual_root.predicted_price))

    return ForecastError(
        compared=len(time_errors),
        without_truth=without_truth,
        called_without_a_root=without_a_root,
        time_to_turn_mae=(sum(time_errors) / len(time_errors) if time_errors else None),
        extreme_price_error=(sum(price_errors) / len(price_errors) if price_errors else None),
    )


def _economics(
    calls: Sequence[Row],
    *,
    outcomes: Mapping[int, SignalOutcome],
    costs: CostModel,
    risk_per_trade: float,
) -> tuple[float | None, str | None]:
    """Expectancy in R over the rows this arm called, after costs.

    A called row with no recorded outcome raises. Dropping it would price the
    arm on the subset of its calls that happened to be followed up, which
    flatters whichever arm called the rows someone bothered to resolve.
    """
    if not calls:
        return None, "the arm called nothing, and expectancy over no trades is not zero"
    resolved = []
    for row in calls:
        outcome = outcomes.get(row.as_of_ns)
        if outcome is None:
            raise OutcomeMissing(
                f"row at {row.as_of_ns} was called but has no recorded outcome; pricing "
                "the arm on its other calls would score it on the subset someone "
                "happened to resolve"
            )
        resolved.append(outcome)
    try:
        report = economic_report(resolved, costs=costs, risk_per_trade=risk_per_trade)
    except NothingResolved as exc:
        return None, str(exc)
    return report.expectancy_r, None


def _with_increments(arms: dict[str, ArmReport]) -> dict[str, ArmReport]:
    """Fill in each arm's expectancy against `BASELINE_ARM`."""
    baseline = arms[BASELINE_ARM].expectancy_r
    if baseline is None:
        return arms
    filled = dict(arms)
    for arm, report in arms.items():
        if arm == BASELINE_ARM or report.expectancy_r is None:
            continue
        filled[arm] = ArmReport(
            arm=report.arm,
            scored=report.scored,
            calibration=report.calibration,
            calls=report.calls,
            expectancy_r=report.expectancy_r,
            incremental_expectancy_r=report.expectancy_r - baseline,
            roots=report.roots,
            forecast=report.forecast,
            unpriced=report.unpriced,
        )
    return filled


def _rule(arms: dict[str, ArmReport], *, gate: PromotionGate) -> tuple[Verdict, str]:
    """EXP-013's own last sentence: unstable roots or no OOS value, and reject.

    Both conditions are checked, and both are reported when both fail. A verdict
    that stopped at the first would send a reader back to run the experiment
    again with that one fixed, only to meet the second.
    """
    roots = arms["derivative_roots"].roots
    failures: list[str] = []

    if roots is None or roots.presence_rate is None:
        failures.append("no row produced a root to assess")
    else:
        if roots.presence_rate < gate.minimum_presence_rate:
            failures.append(
                f"roots are unstable: a mean presence rate of {roots.presence_rate:.2f} "
                f"against the gate's {gate.minimum_presence_rate:.2f}"
            )
        if roots.horizon_iqr is not None and roots.horizon_iqr > gate.maximum_horizon_iqr:
            failures.append(
                f"roots are unstable: a mean horizon IQR of {roots.horizon_iqr:.2f} "
                f"against the gate's {gate.maximum_horizon_iqr:.2f}"
            )

    gains: dict[str, float] = {}
    for arm in ARMS:
        if arm in CLASSIFIER_ARMS:
            continue
        gain = arms[arm].incremental_expectancy_r
        if gain is not None:
            gains[arm] = gain
    if not gains:
        failures.append(
            f"no derivative arm could be priced against {BASELINE_ARM}, so there is no "
            "incremental expectancy to weigh"
        )
    elif max(gains.values()) <= 0.0:
        best = max(gains, key=lambda arm: gains[arm])
        failures.append(
            f"no OOS value after costs: the best derivative arm ({best}) adds "
            f"{gains[best]:+.4f}R over {BASELINE_ARM}"
        )

    if failures:
        return Verdict.NO_EDGE, "; ".join(failures)
    best = max(gains, key=lambda arm: gains[arm])
    return (
        Verdict.EDGE,
        f"{best} adds {gains[best]:+.4f}R over {BASELINE_ARM} after costs, on roots "
        f"the gate accepts",
    )
