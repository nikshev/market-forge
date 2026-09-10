"""Calibration per horizon, not in aggregate (REQ-WP-023)."""

from __future__ import annotations

import numpy as np
import pytest

from channelflow.dataset import Label, Row
from channelflow.models import HorizonCalibration, calibration, calibration_by_horizon

SECOND = 1_000_000_000


def row(*, at: int, horizon: int, label_class: str = "MAX") -> Row:
    return Row(
        entity="binance:BTCUSDT",
        as_of_ns=at,
        features={"f": 1.0},
        source_max_event_ns=at,
        label=Label(
            label_class=label_class,  # type: ignore[arg-type]
            horizon_end_ns=at + horizon,
            available_ns=at + horizon,
        ),
    )


def series(
    *, horizon: int, n: int, hit: float, predicted: float, start: int = 0
) -> tuple[list[Row], list[float]]:
    """`n` rows at one horizon, of which a `hit` share are the target class."""
    rows: list[Row] = []
    probabilities: list[float] = []
    for index in range(n):
        occurred = index < round(n * hit)
        rows.append(
            row(
                at=start + index * SECOND,
                horizon=horizon,
                label_class="MAX" if occurred else "NO_TURN",
            )
        )
        probabilities.append(predicted)
    return rows, probabilities


@pytest.mark.trace("REQ-WP-023")
def test_each_horizon_gets_its_own_curve() -> None:
    short_rows, short_p = series(horizon=5 * SECOND, n=40, hit=0.5, predicted=0.5)
    long_rows, long_p = series(
        horizon=50 * SECOND, n=40, hit=0.1, predicted=0.9, start=10_000 * SECOND
    )

    report = calibration_by_horizon(
        short_rows + long_rows,
        np.array(short_p + long_p),
        target="MAX",
        minimum_observations=10,
    )

    assert set(report.slices) == {5 * SECOND, 50 * SECOND}
    assert report.slices[5 * SECOND].observations == 40
    assert report.slices[50 * SECOND].observations == 40


@pytest.mark.trace("REQ-WP-023")
def test_the_pooled_figure_hides_what_the_slices_show() -> None:
    """The whole argument for this requirement, as a test.

    One horizon is well calibrated and the other badly. Pooled, the error lands
    between them and looks tolerable; sliced, one of the two is plainly wrong --
    and it is the one a trader acting at that horizon would have relied on.
    """
    good_rows, good_p = series(horizon=5 * SECOND, n=40, hit=0.5, predicted=0.5)
    bad_rows, bad_p = series(
        horizon=50 * SECOND, n=40, hit=0.1, predicted=0.9, start=10_000 * SECOND
    )

    report = calibration_by_horizon(
        good_rows + bad_rows,
        np.array(good_p + bad_p),
        target="MAX",
        minimum_observations=10,
    )

    good = report.slices[5 * SECOND].curve
    bad = report.slices[50 * SECOND].curve
    assert good is not None and bad is not None
    assert good.error < 0.05
    assert bad.error > 0.5
    assert good.error < report.pooled.error < bad.error


@pytest.mark.trace("REQ-WP-023")
def test_a_thin_horizon_is_unmeasured_rather_than_curved() -> None:
    """A slice with three rows reporting a curve reintroduces, one level down,
    the exact defect slicing removes."""
    many_rows, many_p = series(horizon=5 * SECOND, n=40, hit=0.5, predicted=0.5)
    few_rows, few_p = series(
        horizon=50 * SECOND, n=3, hit=0.0, predicted=0.9, start=10_000 * SECOND
    )

    report = calibration_by_horizon(
        many_rows + few_rows,
        np.array(many_p + few_p),
        target="MAX",
        minimum_observations=10,
    )

    thin = report.slices[50 * SECOND]
    assert thin.curve is None
    assert thin.observations == 3
    assert "3" in thin.reason


@pytest.mark.trace("REQ-WP-023")
def test_a_target_that_never_occurs_is_measured_not_unmeasured() -> None:
    """It has observations and no positive outcomes, which is a real
    calibration -- and a bad one. An implementation keying on "no positives"
    rather than "too few rows" would call it unmeasured and hide the finding."""
    rows, probabilities = series(horizon=5 * SECOND, n=40, hit=0.0, predicted=0.8)

    report = calibration_by_horizon(
        rows, np.array(probabilities), target="MAX", minimum_observations=10
    )

    measured = report.slices[5 * SECOND]
    assert measured.curve is not None
    assert measured.observations == 40
    assert measured.curve.error > 0.5


@pytest.mark.trace("REQ-WP-023")
def test_the_minimum_is_the_caller_s() -> None:
    """Principle X. Changing it changes which slices are unmeasured, and nothing
    else."""
    rows, probabilities = series(horizon=5 * SECOND, n=8, hit=0.5, predicted=0.5)
    predicted = np.array(probabilities)

    lenient = calibration_by_horizon(rows, predicted, target="MAX", minimum_observations=5)
    strict = calibration_by_horizon(rows, predicted, target="MAX", minimum_observations=20)

    assert lenient.slices[5 * SECOND].curve is not None
    assert strict.slices[5 * SECOND].curve is None
    assert lenient.pooled.error == strict.pooled.error
    assert lenient.slices[5 * SECOND].observations == strict.slices[5 * SECOND].observations


@pytest.mark.trace("REQ-WP-023")
def test_the_horizon_comes_from_the_row_s_own_label() -> None:
    """A caller who believes the horizons are uniform and is wrong sees the
    horizons that were actually there."""
    mixed = [
        row(at=0, horizon=5 * SECOND),
        row(at=SECOND, horizon=5 * SECOND),
        row(at=2 * SECOND, horizon=9 * SECOND),
    ]

    report = calibration_by_horizon(
        mixed, np.array([0.5, 0.5, 0.5]), target="MAX", minimum_observations=1
    )

    assert set(report.slices) == {5 * SECOND, 9 * SECOND}
    assert report.slices[9 * SECOND].observations == 1


@pytest.mark.trace("REQ-WP-023")
def test_a_misaligned_pair_is_refused() -> None:
    rows, probabilities = series(horizon=5 * SECOND, n=4, hit=0.5, predicted=0.5)

    with pytest.raises(ValueError, match="same length"):
        calibration_by_horizon(
            rows, np.array(probabilities[:2]), target="MAX", minimum_observations=1
        )


@pytest.mark.trace("REQ-WP-023")
def test_no_rows_is_refused() -> None:
    with pytest.raises(ValueError, match="no predictions"):
        calibration_by_horizon([], np.array([]), target="MAX", minimum_observations=1)


@pytest.mark.trace("REQ-WP-023")
def test_the_pooled_figure_is_what_calibration_would_have_said() -> None:
    """Beside the slices, never instead of them -- and the same number, so a
    reader comparing an old report against a new one is comparing like with
    like."""
    rows, probabilities = series(horizon=5 * SECOND, n=40, hit=0.5, predicted=0.5)
    predicted = np.array(probabilities)
    actual = np.array([1.0 if r.label.label_class == "MAX" else 0.0 for r in rows])

    report = calibration_by_horizon(rows, predicted, target="MAX", minimum_observations=1)

    assert report.pooled == calibration(predicted, actual)


@pytest.mark.trace("REQ-WP-023")
def test_a_report_is_a_value() -> None:
    rows, probabilities = series(horizon=5 * SECOND, n=12, hit=0.5, predicted=0.5)
    predicted = np.array(probabilities)

    first = calibration_by_horizon(rows, predicted, target="MAX", minimum_observations=1)
    second = calibration_by_horizon(rows, predicted, target="MAX", minimum_observations=1)

    assert isinstance(first, HorizonCalibration)
    assert first == second
