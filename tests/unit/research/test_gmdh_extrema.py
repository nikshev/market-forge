"""EXP-013's four arms and the verdict on the derivative route (REQ-EXP-013)."""

from __future__ import annotations

import pytest

from channelflow.backtest import CostModel, CostsRequired, Outcome, SignalOutcome
from channelflow.dataset import CertifiedDataset, Label, Row, WalkForwardFolds, certify
from channelflow.research.gmdh_extrema import (
    ARMS,
    CLASSIFIER_ARMS,
    ExtremaComparison,
    OutcomeMissing,
    compare_gmdh_extrema,
)
from channelflow.turning import PathCoefficients, Verdict, assess_root_stability
from channelflow.turning.experiment import DEFAULT_TOLERANCE

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND
COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)

#: A path that peaks at h = 3, and one that runs straight down.
TURNS = PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=10.0)
STRAIGHT = PathCoefficients(c0=0.0, c1=-2.0, c2=0.0, c3=0.0, horizon=10.0)
#: The same peak with the horizon closed in around it. The root sits at 3.0 and
#: the horizon ends at 3.05, so a perturbation within tolerance pushes it out --
#: which is section 13A.12's whole subject.
TURNS_AT_THE_EDGE = TURNS.model_copy(update={"horizon": 3.05})


def _row(index: int, *, features: dict[str, float], turning: bool) -> Row:
    as_of_ns = index * SECOND
    return Row(
        entity="BTCUSDT",
        as_of_ns=as_of_ns,
        features=features,
        source_max_event_ns=as_of_ns,
        label=Label(
            label_class="MAX" if turning else "NO_TURN",
            horizon_end_ns=as_of_ns + HORIZON_NS,
            available_ns=as_of_ns + HORIZON_NS,
        ),
    )


def linear_rows(n: int = 120) -> list[Row]:
    """A target a logistic model can learn: the sign of `slope` decides it."""
    return [
        _row(
            index,
            # The drift makes every feature vector distinct, so `require_disjoint`
            # does not read a repeated vector as a shared row.
            features={
                "slope": (1.0 if index % 2 == 0 else -1.0) + index * 1e-6,
                "curvature": float(index % 3) - 1.0,
            },
            turning=index % 2 == 0,
        )
        for index in range(n)
    ]


def interaction_rows(n: int = 160) -> list[Row]:
    """A target no linear model can learn: the *product* of two signs decides it.

    The control for the `EDGE` branch. A logistic baseline predicts the base rate
    everywhere here, so an arm that finds the interaction calls a genuinely
    better subset -- which is what "adds OOS value" has to mean.
    """
    rows = []
    for index in range(n):
        a = 1.0 if index % 2 == 0 else -1.0
        b = 1.0 if (index // 2) % 2 == 0 else -1.0
        rows.append(
            _row(index, features={"a": a + index * 1e-6, "b": b + index * 1e-6}, turning=a * b > 0)
        )
    return rows


def split_rows(n: int = 160) -> list[Row]:
    """A label the classifier can learn on rows whose path does not always turn.

    `a > 0` decides the label, so a logistic model is confident on those rows;
    the forward path turns only when `a > 0` *and* `b > 0`. The rows in between
    are the ones the ensemble reaches on its classifier half alone.
    """
    rows = []
    for index in range(n):
        a = 1.0 if index % 2 == 0 else -1.0
        b = 1.0 if (index // 2) % 2 == 0 else -1.0
        rows.append(
            _row(index, features={"a": a + index * 1e-6, "b": b + index * 1e-6}, turning=a > 0)
        )
    return rows


def paths(rows: list[Row], *, turns: PathCoefficients = TURNS) -> dict[int, PathCoefficients]:
    """A forward path per row, label-side by PRD section 24.2's permission."""
    return {row.as_of_ns: (turns if row.label.label_class == "MAX" else STRAIGHT) for row in rows}


def both_signs_paths(rows: list[Row]) -> dict[int, PathCoefficients]:
    """Turns only where both features are positive, whatever the label says."""
    return {
        row.as_of_ns: (TURNS if row.features["a"] > 0.5 and row.features["b"] > 0.5 else STRAIGHT)
        for row in rows
    }


def unlearnable_paths(rows: list[Row]) -> dict[int, PathCoefficients]:
    """Paths keyed to nothing the features carry.

    Every third row turns, on a period neither feature follows, so the
    coefficient networks can only predict the average path -- and that average
    turns. Rows whose true path runs straight then get a promoted root, which is
    the only way to reach a call with no truth behind it.
    """
    return {row.as_of_ns: (TURNS if index % 3 == 0 else STRAIGHT) for index, row in enumerate(rows)}


def outcomes(rows: list[Row]) -> dict[int, SignalOutcome]:
    """A win where the label turned, a loss where it did not."""
    built = {}
    for row in rows:
        won = row.label.label_class == "MAX"
        built[row.as_of_ns] = SignalOutcome(
            horizon_end_ns=row.label.horizon_end_ns,
            first_target_time_ns=row.as_of_ns + SECOND if won else None,
            first_invalidation_time_ns=None if won else row.as_of_ns + SECOND,
            mfe_pct=0.03 if won else 0.001,
            mae_pct=0.002 if won else 0.02,
            return_h=0.03 if won else -0.02,
            outcome=Outcome.TARGET if won else Outcome.STOP,
        )
    return built


def certified(rows: list[Row]) -> CertifiedDataset:
    """REQ-US-007's gate: this fits models, so it takes a certificate."""
    return certify(rows, WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(rows))


def run(
    rows: list[Row],
    *,
    features: tuple[str, ...],
    path_targets: dict[int, PathCoefficients] | None = None,
    call_threshold: float = 0.5,
    **kwargs: object,
) -> ExtremaComparison:
    return compare_gmdh_extrema(
        certified(rows),
        feature_names=features,
        path_targets=path_targets if path_targets is not None else paths(rows),
        target="MAX",
        outcomes=outcomes(rows),
        costs=COSTS,
        risk_per_trade=0.01,
        call_threshold=call_threshold,
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.trace("REQ-EXP-013")
def test_all_four_arms_the_prd_names_are_compared() -> None:
    """EXP-013's list, in its order: direct classifier only; GMDH direct
    turning-point classifier; GMDH forward path + derivative roots; ensemble."""
    assert ARMS == ("direct_only", "gmdh_direct", "derivative_roots", "ensemble")

    report = run(linear_rows(), features=("slope", "curvature"))

    assert list(report.arms) == list(ARMS)


@pytest.mark.trace("REQ-EXP-013")
def test_every_metric_the_prd_names_is_reported() -> None:
    """Root presence rate, root horizon IQR, turn-type agreement, time-to-turn
    MAE, extreme-price error, calibration, incremental expectancy after costs."""
    report = run(linear_rows(), features=("slope", "curvature"))

    for arm in report.arms.values():
        assert arm.scored.model_brier is not None
        assert arm.calibration is not None

    derivative = report.arms["derivative_roots"]
    assert derivative.roots is not None
    assert derivative.roots.presence_rate is not None
    assert derivative.roots.horizon_iqr is not None
    assert derivative.roots.turn_type_agreement is not None
    assert derivative.forecast is not None
    assert derivative.forecast.time_to_turn_mae is not None
    assert derivative.forecast.extreme_price_error is not None
    assert derivative.incremental_expectancy_r is not None


@pytest.mark.trace("REQ-EXP-013")
def test_a_classifier_arm_names_no_time_and_no_price() -> None:
    """And is not scored on either.

    A classifier outputs a probability and nothing else. Giving it a
    time-to-turn error borrowed from somewhere else would judge the cheap arm on
    a promise it never made -- and the whole point of EXP-013 is what the
    expensive arm buys.
    """
    report = run(linear_rows(), features=("slope", "curvature"))

    for name in CLASSIFIER_ARMS:
        assert report.arms[name].roots is None
        assert report.arms[name].forecast is None


@pytest.mark.trace("REQ-EXP-013")
def test_the_presence_rate_is_averaged_over_the_rows_that_had_a_root() -> None:
    """Not over every scored row.

    The presence rate is a property of a root: the share of perturbed members
    that still found it. Half the paths in this fixture run straight, so
    averaging over every row would report 0.50 and fail the gate -- reading as
    "the roots are unstable" about roots that are perfectly stable.
    """
    report = run(linear_rows(), features=("slope", "curvature"))

    roots = report.arms["derivative_roots"].roots
    assert roots is not None
    assert roots.rows_with_a_root * 2 == roots.rows, "half the fixture's paths turn"
    assert roots.presence_rate == 1.0


@pytest.mark.trace("REQ-EXP-013")
def test_unstable_roots_are_rejected() -> None:
    """EXP-013's own last sentence, first half.

    The root sits at h = 3.0 with the horizon ending at 3.05, so a perturbation
    inside the tolerance pushes it past the end -- section 13A.11's "a root can
    appear from tiny coefficient changes", read the other way round.
    """
    report = run(
        interaction_rows(),
        features=("a", "b"),
        path_targets=paths(interaction_rows(), turns=TURNS_AT_THE_EDGE),
    )

    assert report.verdict is Verdict.NO_EDGE
    assert "unstable" in report.reason


@pytest.mark.trace("REQ-EXP-013")
def test_a_derivative_arm_that_adds_nothing_is_rejected() -> None:
    """The second half. Every arm calls the same rows on this fixture, so the
    derivative route buys nothing for its four networks and its lattice."""
    report = run(linear_rows(), features=("slope", "curvature"))

    assert report.verdict is Verdict.NO_EDGE
    assert "no OOS value" in report.reason
    assert report.arms["derivative_roots"].incremental_expectancy_r == 0.0


@pytest.mark.trace("REQ-EXP-013")
def test_both_reasons_are_reported_when_both_fail() -> None:
    """A verdict that stopped at the first would send a reader back to run the
    experiment again with that one fixed, only to meet the second."""
    report = run(
        interaction_rows(),
        features=("a", "b"),
        path_targets=paths(interaction_rows(), turns=TURNS_AT_THE_EDGE),
    )

    assert "unstable" in report.reason
    assert "incremental expectancy" in report.reason or "no OOS value" in report.reason


@pytest.mark.trace("REQ-EXP-013")
def test_a_derivative_arm_that_adds_value_is_accepted() -> None:
    """The control. Without it, `NO_EDGE` everywhere would be consistent with an
    experiment that cannot conclude anything at all."""
    report = run(interaction_rows(), features=("a", "b"))

    assert report.verdict is Verdict.EDGE
    increment = report.arms["derivative_roots"].incremental_expectancy_r
    assert increment is not None and increment > 0.0


@pytest.mark.trace("REQ-EXP-013")
def test_the_increment_is_measured_against_the_direct_classifier() -> None:
    """ "Incremental expectancy" is incremental over something, and EXP-013's
    first arm is what the other three have to beat."""
    report = run(interaction_rows(), features=("a", "b"))

    baseline = report.arms["direct_only"]
    assert baseline.incremental_expectancy_r is None, "the baseline is not its own increment"
    assert baseline.expectancy_r is not None

    for name in ("derivative_roots", "ensemble"):
        arm = report.arms[name]
        assert arm.expectancy_r is not None
        assert arm.incremental_expectancy_r == pytest.approx(
            arm.expectancy_r - baseline.expectancy_r
        )


@pytest.mark.trace("REQ-EXP-013")
def test_the_ensemble_keeps_its_classifier_half() -> None:
    """The mean, not the product.

    A product is zero wherever no root was promoted, which would silence the
    ensemble on exactly the rows where the classifier is the only thing
    speaking. Here `a > 0` decides the label and the path turns only when both
    features are positive, so those rows exist -- and the ensemble reaches them.
    """
    rows = split_rows()
    report = run(rows, features=("a", "b"), path_targets=both_signs_paths(rows), call_threshold=0.4)

    forecast = report.arms["ensemble"].forecast
    assert forecast is not None
    assert forecast.called_without_a_root > 0
    assert report.arms["ensemble"].calls > report.arms["derivative_roots"].calls


@pytest.mark.trace("REQ-EXP-013")
def test_a_called_row_without_an_outcome_is_refused() -> None:
    """Dropping it would price the arm on the subset of its calls that someone
    happened to resolve, which flatters whichever arm called those rows."""
    rows = linear_rows()
    dataset = certified(rows)
    # A row every arm calls, and one a fold actually scores: a training row's
    # outcome is never looked up, so dropping one would prove nothing.
    called = next(
        row for fold in dataset.folds for row in fold.validate if row.label.label_class == "MAX"
    )
    incomplete = outcomes(rows)
    incomplete.pop(called.as_of_ns)

    with pytest.raises(OutcomeMissing, match=str(called.as_of_ns)):
        compare_gmdh_extrema(
            dataset,
            feature_names=("slope", "curvature"),
            path_targets=paths(rows),
            target="MAX",
            outcomes=incomplete,
            costs=COSTS,
            risk_per_trade=0.01,
            call_threshold=0.5,
        )


@pytest.mark.trace("REQ-EXP-013")
def test_the_economics_refuse_to_run_without_costs() -> None:
    """PRD section 41 rule 9, and [[ADR-009]]: a gross figure gets quoted as the
    figure, because the caveat does not travel with the number."""
    rows = linear_rows()

    with pytest.raises(CostsRequired):
        compare_gmdh_extrema(
            certified(rows),
            feature_names=("slope", "curvature"),
            path_targets=paths(rows),
            target="MAX",
            outcomes=outcomes(rows),
            costs=None,  # type: ignore[arg-type]
            risk_per_trade=0.01,
            call_threshold=0.5,
        )


@pytest.mark.trace("REQ-EXP-013")
def test_the_call_threshold_is_required_and_bounded() -> None:
    """It decides which rows every arm is judged on, and every economic figure
    in the report moves with it. PRD section 13A.27's warning applies."""
    rows = linear_rows()

    with pytest.raises(TypeError):
        compare_gmdh_extrema(  # type: ignore[call-arg]
            certified(rows),
            feature_names=("slope", "curvature"),
            path_targets=paths(rows),
            target="MAX",
            outcomes=outcomes(rows),
            costs=COSTS,
            risk_per_trade=0.01,
        )

    with pytest.raises(ValueError, match="outside"):
        run(rows, features=("slope", "curvature"), call_threshold=0.0)


@pytest.mark.trace("REQ-EXP-013")
def test_two_runs_produce_equal_reports() -> None:
    rows = linear_rows()

    first = run(rows, features=("slope", "curvature"))
    second = run(rows, features=("slope", "curvature"))

    assert first.verdict == second.verdict
    assert first.reason == second.reason
    assert first.arms["derivative_roots"].roots == second.arms["derivative_roots"].roots
    assert first.arms["ensemble"].forecast == second.arms["ensemble"].forecast


@pytest.mark.trace("REQ-EXP-013")
def test_the_horizon_iqr_is_the_spread_of_the_roots_that_exist() -> None:
    """Same denominator as the presence rate, and for the same reason.

    Half this fixture's paths run straight. Averaging their absent spread in as
    zero halves the reported IQR, which reads as roots that agree twice as well
    as they do -- and the gate is a *maximum*, so the error is in the direction
    that lets an unstable set through.

    The reference is the production stability function's own answer for the path
    the fixture uses, not a number written down here.
    """
    report = run(linear_rows(), features=("slope", "curvature"))

    roots = report.arms["derivative_roots"].roots
    assert roots is not None
    assert roots.rows_with_a_root * 2 == roots.rows, "half the fixture's paths turn"
    reference = assess_root_stability(TURNS, tolerance=DEFAULT_TOLERANCE)
    assert roots.horizon_iqr == pytest.approx(reference.horizon_iqr, rel=0.01)


@pytest.mark.trace("REQ-EXP-013")
def test_a_call_with_no_true_turn_is_counted_rather_than_scored() -> None:
    """An arm is not wrong about a time that does not exist.

    Scoring those rows as perfect hits -- zero error, because there is nothing to
    subtract -- would reward an arm for calling turns on paths that never turn,
    which is the opposite of what the error is for. So every call lands in
    exactly one of three counts, and the three add up to the calls.
    """
    rows = split_rows()
    report = run(
        rows, features=("a", "b"), path_targets=unlearnable_paths(rows), call_threshold=0.4
    )

    arm = report.arms["derivative_roots"]
    forecast = arm.forecast
    assert forecast is not None
    assert forecast.without_truth > 0, "the fixture has to contain the case"
    assert forecast.compared > 0, "and the other case too"
    # The paths here are quadratic, so a call names at most one root.
    assert forecast.compared + forecast.without_truth + forecast.called_without_a_root == arm.calls
