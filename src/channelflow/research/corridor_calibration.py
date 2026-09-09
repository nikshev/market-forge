"""EXP-009: which forecast corridor actually covers what it claims.

# @trace: REQ-EXP-009

    Compare: empirical residual quantile; parametric std band; conformal-adjusted
    interval.

    Metric: target coverage with narrowest stable interval.

Two words in that metric do the work. **Target coverage** is a promise: an 80%
corridor that contains 62% of what follows is not a narrow corridor, it is a
wrong one. **Narrowest stable** is the tie-break among the corridors that keep
the promise -- and "stable" means on every fold, not on average, because a
corridor that covers 95% in one window and 65% in another averages to its target
while being useless in both.

PRD section 13.7 gives the forecast corridor and section 13.8 the conformal
layer: "rolling residual calibration... target coverage 80/90/95% configurable".
The conformal method here is the split-conformal one that description names: take
the recent absolute errors at this horizon and use their quantile as the
half-width. It is the only one of the three that adapts to how wrong the model
has recently been.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from channelflow.bars import Bar
from channelflow.channels import ChannelFitError, ChannelModel, ChannelSnapshot, RollingOLSChannel

#: PRD section 13.8's configurable levels.
SUPPORTED_COVERAGE: tuple[float, ...] = (0.80, 0.90, 0.95)

#: How far ahead the corridor is measured. A research default, held equal across
#: methods because the comparison is between them.
DEFAULT_HORIZON = 10

#: How many recent horizons the conformal method calibrates on. Long enough to
#: hold a quantile, short enough to follow a change in volatility.
DEFAULT_CALIBRATION_WINDOW = 60

#: Fewer measurements than this cannot support a coverage rate. At thirty, one
#: miss moves the reported coverage by three points; below it the number is
#: mostly the last fit.
MIN_MEASUREMENTS = 30


class Method(StrEnum):
    EMPIRICAL_QUANTILE = "empirical_residual_quantile"
    PARAMETRIC_STD = "parametric_std_band"
    CONFORMAL = "conformal_adjusted"


class NoStableCorridor(ValueError):
    """No method held its promised coverage on every fold."""


@dataclass(frozen=True)
class MethodResult:
    """One corridor construction, measured."""

    method: Method
    #: Realized coverage per fold, in fold order.
    coverage_by_fold: tuple[float, ...]
    mean_width_pct: float
    observations: int

    @property
    def worst_coverage(self) -> float:
        return min(self.coverage_by_fold) if self.coverage_by_fold else 0.0

    @property
    def mean_coverage(self) -> float:
        return (
            sum(self.coverage_by_fold) / len(self.coverage_by_fold)
            if self.coverage_by_fold
            else 0.0
        )

    def stable_at(self, target: float) -> bool:
        """Holds the promise on every fold, not on average.

        A corridor covering 95% in one window and 65% in another averages to 80%
        and is useless in both.
        """
        return bool(self.coverage_by_fold) and self.worst_coverage >= target


@dataclass(frozen=True)
class CalibrationReport:
    """Every method, and the narrowest one that kept its promise."""

    results: dict[Method, MethodResult]
    target_coverage: float
    horizon: int
    winner: Method | None
    reason: str = ""


def compare_corridors(
    bars: list[Bar],
    *,
    target_coverage: float,
    model: ChannelModel | None = None,
    horizon: int = DEFAULT_HORIZON,
    folds: int = 4,
    calibration_window: int = DEFAULT_CALIBRATION_WINDOW,
) -> CalibrationReport:
    """Measure all three corridors and pick the narrowest stable one."""
    if target_coverage not in SUPPORTED_COVERAGE:
        raise ValueError(
            f"target coverage {target_coverage} is not one of PRD section 13.8's "
            f"configurable levels {SUPPORTED_COVERAGE}"
        )

    fitter = model or RollingOLSChannel()
    measurements = measure_corridors(
        bars, fitter, horizon=horizon, calibration_window=calibration_window
    )
    if len(measurements) < MIN_MEASUREMENTS:
        raise ChannelFitError(
            f"{len(bars)} bars gave {len(measurements)} measurement(s) under a "
            f"{fitter.lookback}-bar lookback, a {calibration_window}-bar calibration "
            f"window and a {horizon}-bar horizon; a coverage rate over fewer than "
            f"{MIN_MEASUREMENTS} is mostly the last fit"
        )

    results: dict[Method, MethodResult] = {}
    for method in Method:
        widths = [m.widths[method] for m in measurements]
        hits = [m.hits[method] for m in measurements]
        results[method] = MethodResult(
            method=method,
            coverage_by_fold=_by_fold(hits, folds=folds),
            mean_width_pct=float(np.mean(widths)),
            observations=len(measurements),
        )

    winner, reason = pick_winner(results, target_coverage=target_coverage)
    return CalibrationReport(
        results=results,
        target_coverage=target_coverage,
        horizon=horizon,
        winner=winner,
        reason=reason,
    )


def pick_winner(
    results: dict[Method, MethodResult], *, target_coverage: float
) -> tuple[Method | None, str]:
    """The narrowest corridor that held its promise on every fold.

    Public because it is the whole metric -- "target coverage with narrowest
    stable interval" -- and a real run rarely produces the case that matters: a
    narrow corridor that misses the target beside a wider one that does not.

    Never the narrowest overall as a fallback. A corridor that does not cover
    what it claims is not a corridor, and offering it because nothing else
    qualified is the failure the word "stable" is in the metric to prevent.
    """
    stable = [r for r in results.values() if r.stable_at(target_coverage)]
    if not stable:
        return None, (
            f"no method held {target_coverage:.0%} on every fold; the narrowest "
            "corridor among those that failed is still one that does not cover what "
            "it claims"
        )
    best = min(stable, key=lambda r: (r.mean_width_pct, r.method.value))
    return best.method, f"narrowest corridor holding {target_coverage:.0%} on every fold"


@dataclass(frozen=True)
class Measurement:
    """One instant: how wide each corridor was, and whether it contained the close.

    Public because the sequence is where one property can be seen at all: the
    conformal method must not calibrate on the outcome it is about to be judged
    on, and that shows as a width which does not react until the instant *after*
    a large error.
    """

    index: int
    widths: dict[Method, float]
    hits: dict[Method, bool]


def measure_corridors(
    bars: list[Bar],
    model: ChannelModel,
    *,
    horizon: int,
    calibration_window: int,
) -> list[Measurement]:
    """Fit at each instant, project to the horizon, and see what happened."""
    start = max(model.lookback, calibration_window) - 1
    errors: list[float] = []
    measurements: list[Measurement] = []

    for index in range(start, len(bars) - horizon):
        snapshot = model.fit(bars, as_of_ns=bars[index].close_time_ns)
        centre = _forecast_centre(snapshot, horizon=horizon)
        realized = float(bars[index + horizon].close)

        # The error this fit would have made, kept for the conformal method to
        # calibrate on. Recorded after it is used, so nothing calibrates on its
        # own outcome.
        recent = errors[-calibration_window:]
        widths, hits = _corridors(
            snapshot, centre=centre, realized=realized, recent=recent, horizon=horizon
        )
        measurements.append(Measurement(index=index, widths=widths, hits=hits))
        errors.append(abs(np.log(realized) - np.log(centre)))

    return measurements


def _forecast_centre(snapshot: ChannelSnapshot, *, horizon: int) -> float:
    """PRD section 13.7's forecast centre: the channel projected along its slope.

    Projecting flat would be a different forecast, and on a trending channel a
    corridor around the wrong centre misses on one side however wide it is.
    """
    return float(np.exp(np.log(snapshot.center_now) + snapshot.slope_log_per_bar * horizon))


def _corridors(
    snapshot: ChannelSnapshot,
    *,
    centre: float,
    realized: float,
    recent: Sequence[float],
    horizon: int,
) -> tuple[dict[Method, float], dict[Method, bool]]:
    """The three half-widths at this instant, in log space, and whether each held."""
    half_empirical = (np.log(snapshot.upper_now) - np.log(snapshot.lower_now)) / 2.0
    # The parametric band from the same channel's width, read as a standard
    # deviation rather than as a quantile span: 1.2816 sigmas is the 80% band a
    # residual-quantile channel targets, so dividing recovers the sigma.
    sigma = half_empirical / 1.2816
    half_parametric = 1.6449 * sigma
    half_conformal = float(np.quantile(recent, 0.9)) if len(recent) >= 10 else half_empirical

    error = abs(np.log(realized) - np.log(centre))
    widths = {
        Method.EMPIRICAL_QUANTILE: float(2.0 * half_empirical),
        Method.PARAMETRIC_STD: float(2.0 * half_parametric),
        Method.CONFORMAL: float(2.0 * half_conformal),
    }
    hits = {
        Method.EMPIRICAL_QUANTILE: bool(error <= half_empirical),
        Method.PARAMETRIC_STD: bool(error <= half_parametric),
        Method.CONFORMAL: bool(error <= half_conformal),
    }
    return widths, hits


def _by_fold(hits: Sequence[bool], *, folds: int) -> tuple[float, ...]:
    """Coverage within each chronological fold.

    Chronological rather than pooled, because a corridor that works in a calm
    quarter and fails in a volatile one is the failure this experiment exists to
    find, and pooling hides it.
    """
    if folds < 1 or len(hits) < folds:
        return (float(np.mean(hits)),) if hits else ()
    size = len(hits) // folds
    return tuple(float(np.mean(hits[index * size : (index + 1) * size])) for index in range(folds))
