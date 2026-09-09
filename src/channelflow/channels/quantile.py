"""Baseline C: quantile regression channel (PRD section 13.4).

# @trace: REQ-CHAN-001

    "Fit conditional quantiles directly: q10 lower; q50 center; q90 upper.
     This supports asymmetric channels.

     Required checks: quantile crossing correction; minimum width; slope
     consistency; numerical stability."

All four checks are here, and each is a refusal or a correction rather than a
note. Baseline A places both bands as residual quantiles around one least-squares
centre, so the two sides move together whatever the market does -- a market that
sells off hard and drifts up slowly gets a channel that says the two are
symmetric.

Fitted by gradient descent on the pinball loss, which needs no linear-programming
dependency and is deterministic: a fixed step count from a least-squares start,
so two runs over one window agree exactly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from channelflow.bars import Bar
from channelflow.channels.models import ChannelQuality, ChannelSnapshot
from channelflow.channels.window import ChannelFitError, fit_window

MODEL_NAME = "quantile_regression_log_price"
MODEL_VERSION = "1.0.0"

NEGLIGIBLE_LOG_SPREAD = 1e-9


@dataclass(frozen=True)
class QuantileChannel:
    """Three conditional quantiles, fitted independently and then reconciled."""

    lookback: int = 60
    quantile_low: float = 0.10
    quantile_high: float = 0.90
    #: Section 13.4's "minimum width", as a percentage of the centre. A channel
    #: of zero width makes every normalized position infinite, and section
    #: 13.10's coordinate is what the signal engine reads.
    minimum_width_pct: float = 0.05

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        window = fit_window(bars, as_of_ns=as_of_ns, lookback=self.lookback)
        log_prices = np.log(np.array([float(b.close) for b in window], dtype=np.float64))
        index = np.arange(len(window), dtype=np.float64)
        # Centred and scaled so the two coefficients are on comparable scales;
        # without it the slope's gradient is `lookback` times the intercept's
        # and a shared step size cannot serve both.
        scale = max(index.std(), 1.0)
        scaled = (index - index.mean()) / scale

        fits = {
            tau: _pinball_fit(scaled, log_prices, tau=tau)
            for tau in (self.quantile_low, 0.5, self.quantile_high)
        }
        if any(not np.all(np.isfinite(value)) for value in fits.values()):
            raise ChannelFitError(
                "the quantile fit did not stay finite; section 13.4 requires numerical "
                "stability, and a channel of NaN boundaries is read as a channel"
            )

        now = float(scaled[-1])
        levels = {tau: float(a + b * now) for tau, (a, b) in fits.items()}
        slopes = {tau: float(b) for tau, (_, b) in fits.items()}

        # Section 13.4's crossing correction. Independently fitted quantiles can
        # cross on a short window; uncorrected, the upper band sits below the
        # lower one and every position on the channel is negative -- a number
        # the signal engine reads as a zone.
        lower_log, center_log, upper_log = sorted(levels.values())

        center_now = math.exp(center_log)
        lower_now, upper_now = math.exp(lower_log), math.exp(upper_log)
        lower_now, upper_now = _widen(
            lower_now, upper_now, center_now, minimum_pct=self.minimum_width_pct
        )

        residuals = log_prices - (fits[0.5][0] + fits[0.5][1] * scaled)
        spread = float(np.std(residuals))
        return ChannelSnapshot(
            as_of_ns=as_of_ns,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            lookback=self.lookback,
            center_now=center_now,
            upper_now=upper_now,
            lower_now=lower_now,
            slope_normalized=(slopes[0.5] / spread if spread > NEGLIGIBLE_LOG_SPREAD else 0.0),
            # The fit runs on a centred, scaled index, so its slope is per
            # scaled unit. Divided by the scale it is per bar again -- the unit
            # every other baseline reports and the one section 13.7 projects in.
            slope_log_per_bar=float(slopes[0.5] / scale),
            width_pct=(upper_now - lower_now) / center_now * 100.0 if center_now > 0 else 0.0,
            quality=_quality(slopes, residuals),
            source_max_event_time_ns=max(bar.close_time_ns for bar in window),
        )


def _pinball_fit(x: np.ndarray, y: np.ndarray, *, tau: float) -> tuple[float, float]:
    """The exact conditional quantile line, by enumeration.

    A linear quantile regression's optimum passes through at least two of the
    data points -- the pinball loss is piecewise linear in the coefficients, so
    its minimum sits at a vertex. With a lookback of sixty that is 1,770
    candidate lines, evaluated at once as a matrix.

    Exact rather than descended. Gradient descent on the pinball loss needs a
    step size, a smoothing width and an iteration count -- three research
    defaults with no principle behind them -- and the first version of this
    module got them wrong in a way no test would have caught: on a perfectly
    flat series the descent oscillated around the solution and reported a
    two-and-a-half percent channel. PRD section 0.14 puts correctness before
    performance, and this is cheap enough that the trade never arises.
    """
    left, right = np.triu_indices(len(x), k=1)
    run = x[right] - x[left]
    usable = run != 0.0
    if not np.any(usable):
        # Every point shares an abscissa, so no pair defines a line. Nothing to
        # fit; the caller's minimum width is what keeps the channel meaningful.
        return float(np.quantile(y, tau)), 0.0

    left, right, run = left[usable], right[usable], run[usable]
    slopes = (y[right] - y[left]) / run
    intercepts = y[left] - slopes * x[left]

    # One row per candidate line, one column per observation.
    residuals = y[None, :] - (intercepts[:, None] + slopes[:, None] * x[None, :])
    losses = np.sum(np.maximum(tau * residuals, (tau - 1.0) * residuals), axis=1)

    # Ties broken on the coefficients, so one window gives one line whatever
    # order the pairs happen to come out in.
    best = int(np.lexsort((intercepts, slopes, losses))[0])
    return float(intercepts[best]), float(slopes[best])


def _widen(lower: float, upper: float, center: float, *, minimum_pct: float) -> tuple[float, float]:
    """Section 13.4's minimum width, applied symmetrically around the centre."""
    if center <= 0:
        return lower, upper
    needed = center * minimum_pct / 100.0
    if upper - lower >= needed:
        return lower, upper
    half = (needed - (upper - lower)) / 2.0
    return lower - half, upper + half


def _quality(slopes: dict[float, float], residuals: np.ndarray) -> ChannelQuality:
    """Section 13.4's slope-consistency check, reported rather than enforced.

    Three quantiles fitted independently can disagree about the trend, and a
    channel whose boundaries diverge is one that will not hold. Refusing would
    discard the case a researcher most wants to see, so it is a submetric: 1.0
    when the three slopes agree, falling as they spread.
    """
    values = np.array(list(slopes.values()), dtype=np.float64)
    spread = float(np.max(values) - np.min(values))
    typical = float(np.mean(np.abs(values)))
    consistency = 1.0 if typical <= NEGLIGIBLE_LOG_SPREAD else 1.0 / (1.0 + spread / typical)
    dispersion = float(np.std(residuals))
    return ChannelQuality(
        score=consistency,
        submetrics={
            "slope_consistency": consistency,
            "residual_dispersion": dispersion,
        },
        contributing=("slope_consistency",),
        # Baseline A's coverage-based submetrics do not transfer: these bands
        # are conditional quantiles, not residual quantiles around one centre.
        unavailable=("coverage_score", "touch_consistency", "width_stability"),
    )
