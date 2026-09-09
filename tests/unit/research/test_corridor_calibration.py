"""EXP-009's forecast corridor calibration (REQ-EXP-009)."""

from __future__ import annotations

import pytest

from channelflow.channels import ChannelFitError, RollingOLSChannel
from channelflow.research.corridor_calibration import (
    SUPPORTED_COVERAGE,
    Method,
    MethodResult,
    compare_corridors,
    measure_corridors,
    pick_winner,
)
from tests.unit.channels.conftest import log_linear_series


def result(method: Method, *, coverage: tuple[float, ...], width: float) -> MethodResult:
    return MethodResult(
        method=method, coverage_by_fold=coverage, mean_width_pct=width, observations=100
    )


def series(n: int = 400, *, noise: float = 0.01):
    return log_linear_series(n, slope_per_bar=0.0005, noise=noise)


@pytest.mark.trace("REQ-EXP-009")
def test_all_three_methods_are_measured() -> None:
    """EXP-009 names three: empirical quantile, parametric band, conformal."""
    report = compare_corridors(series(), target_coverage=0.80)

    assert set(report.results) == set(Method)
    assert len(Method) == 3
    assert all(r.observations > 0 for r in report.results.values())


@pytest.mark.trace("REQ-EXP-009")
def test_the_narrowest_stable_corridor_wins_not_the_narrowest() -> None:
    """The metric in full: "target coverage with narrowest stable interval".

    The narrow corridor here misses the target; the wider one holds it. Choosing
    on width alone picks a corridor that does not cover what it claims.
    """
    results = {
        Method.EMPIRICAL_QUANTILE: result(
            Method.EMPIRICAL_QUANTILE, coverage=(0.82, 0.81, 0.83), width=0.05
        ),
        Method.PARAMETRIC_STD: result(
            Method.PARAMETRIC_STD, coverage=(0.99, 0.99, 0.99), width=0.09
        ),
        Method.CONFORMAL: result(Method.CONFORMAL, coverage=(0.60, 0.61, 0.59), width=0.02),
    }

    winner, reason = pick_winner(results, target_coverage=0.80)

    assert winner is Method.EMPIRICAL_QUANTILE
    assert "narrowest" in reason


@pytest.mark.trace("REQ-EXP-009")
def test_stability_is_per_fold_not_on_average() -> None:
    """A corridor covering 95% in one window and 65% in another averages to its
    target and is useless in both. "Stable" is in the metric for this case."""
    swinging = result(Method.CONFORMAL, coverage=(0.95, 0.65, 0.95, 0.65), width=0.02)
    steady = result(Method.EMPIRICAL_QUANTILE, coverage=(0.81, 0.82, 0.80, 0.81), width=0.06)

    assert swinging.mean_coverage == pytest.approx(0.80)
    assert not swinging.stable_at(0.80)
    assert steady.stable_at(0.80)

    winner, _ = pick_winner(
        {Method.CONFORMAL: swinging, Method.EMPIRICAL_QUANTILE: steady},
        target_coverage=0.80,
    )
    assert winner is Method.EMPIRICAL_QUANTILE


@pytest.mark.trace("REQ-EXP-009")
def test_with_nothing_stable_there_is_no_winner() -> None:
    """And the narrowest failure is not offered instead: a corridor that does
    not cover what it claims is not a corridor."""
    results = {
        method: result(method, coverage=(0.5, 0.5), width=0.01 * (index + 1))
        for index, method in enumerate(Method)
    }

    winner, reason = pick_winner(results, target_coverage=0.90)

    assert winner is None
    assert "does not cover what it claims" in reason


@pytest.mark.trace("REQ-EXP-009")
def test_a_tie_on_width_is_broken_by_name() -> None:
    """Two corridors of the same width must not swap between runs."""
    results = {
        Method.EMPIRICAL_QUANTILE: result(
            Method.EMPIRICAL_QUANTILE, coverage=(0.9, 0.9), width=0.05
        ),
        Method.CONFORMAL: result(Method.CONFORMAL, coverage=(0.9, 0.9), width=0.05),
    }

    assert pick_winner(results, target_coverage=0.80)[0] is Method.CONFORMAL


@pytest.mark.trace("REQ-EXP-009")
def test_only_the_prds_coverage_levels_are_accepted() -> None:
    """PRD §13.8: "target coverage 80/90/95% configurable". A level outside that
    set is a different promise, and the report would carry it as if it were
    one of these."""
    assert SUPPORTED_COVERAGE == (0.80, 0.90, 0.95)

    with pytest.raises(ValueError, match="configurable levels"):
        compare_corridors(series(), target_coverage=0.5)


@pytest.mark.trace("REQ-EXP-009")
def test_a_wider_target_needs_a_wider_corridor() -> None:
    """The measure responds to what it measures: at 95% the corridors that hold
    are a subset of those that hold at 80%."""
    at_80 = compare_corridors(series(), target_coverage=0.80)
    at_95 = compare_corridors(series(), target_coverage=0.95)

    holding_80 = {m for m, r in at_80.results.items() if r.stable_at(0.80)}
    holding_95 = {m for m, r in at_95.results.items() if r.stable_at(0.95)}

    assert holding_95 <= holding_80


@pytest.mark.trace("REQ-EXP-009")
def test_the_forecast_centre_follows_the_channels_slope() -> None:
    """PRD §13.7's forecast centre. Projected flat, a corridor on a trending
    channel misses on one side however wide it is -- so a trending series would
    show far worse coverage than a flat one, and it does not.
    """
    flat = compare_corridors(
        log_linear_series(400, slope_per_bar=0.0, noise=0.01), target_coverage=0.80
    )
    trending = compare_corridors(
        log_linear_series(400, slope_per_bar=0.004, noise=0.01), target_coverage=0.80
    )

    for method in Method:
        assert trending.results[method].mean_coverage >= (
            flat.results[method].mean_coverage - 0.15
        ), f"{method} loses coverage on a trend, so the centre is not being projected"


@pytest.mark.trace("REQ-EXP-009")
def test_a_series_too_short_is_refused() -> None:
    """A corridor measured over a handful of fits is not measured."""
    with pytest.raises(ChannelFitError):
        compare_corridors(log_linear_series(70), target_coverage=0.80)


@pytest.mark.trace("REQ-EXP-009")
def test_two_runs_produce_equal_reports() -> None:
    bars = series()

    assert compare_corridors(bars, target_coverage=0.80) == compare_corridors(
        bars, target_coverage=0.80
    )


@pytest.mark.trace("REQ-EXP-009")
def test_the_conformal_corridor_adapts_where_the_others_do_not() -> None:
    """PRD §13.8's "rolling residual calibration". The conformal half-width comes
    from how wrong this model has recently been, so on a series whose volatility
    changes it should not track the channel's own width the way the other two
    do."""
    quiet_then_loud = log_linear_series(200, noise=0.002) + [
        bar.model_copy(update={"first_trade_id": f"x-{index}"})
        for index, bar in enumerate(log_linear_series(200, noise=0.02, index_offset=200))
    ]

    report = compare_corridors(quiet_then_loud, target_coverage=0.80, model=RollingOLSChannel())

    conformal = report.results[Method.CONFORMAL]
    empirical = report.results[Method.EMPIRICAL_QUANTILE]
    assert conformal.mean_width_pct != pytest.approx(empirical.mean_width_pct, rel=0.01)


@pytest.mark.trace("REQ-EXP-009")
def test_the_conformal_corridor_does_not_calibrate_on_its_own_outcome() -> None:
    """The leak this experiment would be worthless with.

    A corridor whose half-width comes from the errors *including* the one it is
    about to be judged on widens exactly when it needs to and reports coverage
    that no live system could achieve. The width must not react until the
    instant after a large error.

    Here one bar jumps ten percent. The conformal width at the fit whose horizon
    lands on it is the pre-jump width; a later fit's is not.
    """
    bars = list(log_linear_series(400, noise=0.002))
    shock = 300
    bars[shock] = bars[shock].model_copy(
        update={"close": type(bars[shock].close)(str(float(bars[shock].close) * 1.10))}
    )

    measurements = measure_corridors(bars, RollingOLSChannel(), horizon=10, calibration_window=60)
    by_index = {m.index: m for m in measurements}

    # The fit whose horizon lands on the shocked bar, and the one after it.
    landing = by_index[shock - 10]
    following = by_index[shock - 9]

    assert landing.widths[Method.CONFORMAL] < following.widths[Method.CONFORMAL], (
        "the conformal width reacted to the error it was being judged on"
    )


@pytest.mark.trace("REQ-EXP-009")
def test_coverage_is_reported_by_fold_not_pooled() -> None:
    """Pooling hides the failure this experiment exists to find.

    A series that is quiet and then volatile covers well in its early folds and
    badly in its later ones. Pooled, that is one respectable number.
    """
    quiet_then_loud = log_linear_series(200, noise=0.001) + log_linear_series(
        200, noise=0.03, index_offset=200
    )

    report = compare_corridors(quiet_then_loud, target_coverage=0.80, folds=4)

    coverage = report.results[Method.EMPIRICAL_QUANTILE].coverage_by_fold
    assert len(coverage) == 4
    assert max(coverage) - min(coverage) > 0.1, (
        "the folds are indistinguishable, so this fixture cannot tell pooled from per-fold coverage"
    )
