"""Baseline B: robust regression channel (PRD section 13.3).

# @trace: REQ-CHAN-001

    "Candidate estimators: Huber regression; Theil-Sen; RANSAC only as
     experimental due discontinuous model changes.

     Goal: reduce sensitivity to liquidation wicks/outliers."

Huber, fitted by iteratively reweighted least squares, with bands from the
median absolute deviation of the residuals -- REQ-EXP-001 names the pair
"Huber + MAD".

**Theil-Sen and RANSAC are not built.** Section 13.3 lists three candidates and
this is one of them; a module silent about the other two reads as the section,
implemented. RANSAC in particular the PRD marks experimental "due discontinuous
model changes", which is a property worth keeping in view rather than in a
backlog.

Why the least-squares centre is the thing being fixed: a squared loss weights a
30% wick nine hundred times a 1% move, so one liquidation drags the centre and
with it every zone the signal engine reads. Huber's loss is linear past a
threshold, so the wick counts once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from channelflow.bars import Bar
from channelflow.channels.models import ChannelSnapshot
from channelflow.channels.quality import score_channel
from channelflow.channels.window import fit_window

MODEL_NAME = "huber_mad_log_price"
MODEL_VERSION = "1.0.0"

#: Below this the residual spread is floating-point dust from the fit rather
#: than market noise; see `rolling_ols.NEGLIGIBLE_LOG_SPREAD`, same reasoning.
NEGLIGIBLE_LOG_SPREAD = 1e-9

#: 0.6745 is the 75th percentile of the standard normal, so `MAD / 0.6745`
#: estimates the standard deviation of a Gaussian. Keeping the constant named
#: means the band is in the same units as baseline A's quantiles.
MAD_TO_SIGMA = 0.6745


@dataclass(frozen=True)
class HuberChannel:
    """A log-linear channel whose centre a single wick cannot move."""

    lookback: int = 60
    #: In units of the residual scale. 1.345 gives 95% of least squares'
    #: efficiency on clean Gaussian data -- the standard choice, and the reason
    #: a robust fit costs almost nothing when nothing is wrong.
    tuning: float = 1.345
    #: How many robust standard deviations the bands sit at. 1.2816 is the
    #: normal 90th percentile, matching baseline A's default 0.10/0.90 pair.
    band_sigmas: float = 1.2816
    iterations: int = 20
    weights: dict[str, float] | None = None

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        window = fit_window(bars, as_of_ns=as_of_ns, lookback=self.lookback)
        log_prices = np.log(np.array([float(b.close) for b in window], dtype=np.float64))
        index = np.arange(len(window), dtype=np.float64)

        slope, intercept = _irls(index, log_prices, tuning=self.tuning, iterations=self.iterations)
        fitted = intercept + slope * index
        residuals = log_prices - fitted

        scale = _mad(residuals)
        band = self.band_sigmas * scale

        center_log_now = float(fitted[-1])
        center_now = math.exp(center_log_now)
        upper_now = math.exp(center_log_now + band)
        lower_now = math.exp(center_log_now - band)

        slope_normalized = float(slope / scale) if scale > NEGLIGIBLE_LOG_SPREAD else 0.0

        return ChannelSnapshot(
            as_of_ns=as_of_ns,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            lookback=self.lookback,
            center_now=center_now,
            upper_now=upper_now,
            lower_now=lower_now,
            slope_normalized=slope_normalized,
            width_pct=(upper_now - lower_now) / center_now * 100.0 if center_now > 0 else 0.0,
            quality=score_channel(
                residuals=residuals,
                log_prices=log_prices,
                low=-band,
                high=band,
                # The bands are symmetric by construction here, so the coverage
                # they target is the normal mass between them -- not baseline
                # A's empirical quantile span.
                target_coverage=0.80,
                weights=self.weights,
            ),
            source_max_event_time_ns=max(bar.close_time_ns for bar in window),
        )


def _irls(
    index: np.ndarray, log_prices: np.ndarray, *, tuning: float, iterations: int
) -> tuple[float, float]:
    """Huber regression by iteratively reweighted least squares.

    Starts from the least-squares fit and reweights: a residual inside the
    tuning constant keeps its weight, one outside is scaled down in proportion
    to how far out it is. Deterministic and bounded -- a fixed iteration count
    rather than a convergence test, so two runs over one window agree exactly.
    """
    design = np.column_stack([np.ones_like(index), index])
    coefficients = np.linalg.lstsq(design, log_prices, rcond=None)[0]

    for _ in range(iterations):
        residuals = log_prices - design @ coefficients
        scale = _mad(residuals)
        if scale <= NEGLIGIBLE_LOG_SPREAD:
            # Every residual is zero: the fit is exact and reweighting would
            # divide by nothing.
            break
        standardized = np.abs(residuals) / scale
        weights = np.where(standardized <= tuning, 1.0, tuning / standardized)
        weighted = design * weights[:, None]
        updated = np.linalg.lstsq(weighted, log_prices * weights, rcond=None)[0]
        if np.allclose(updated, coefficients):
            break
        coefficients = updated

    return float(coefficients[1]), float(coefficients[0])


def _mad(residuals: np.ndarray) -> float:
    """Median absolute deviation, scaled to a standard deviation."""
    median = float(np.median(residuals))
    return float(np.median(np.abs(residuals - median))) / MAD_TO_SIGMA
