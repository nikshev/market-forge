"""Baseline D: Kalman local linear trend (PRD section 13.5).

# @trace: REQ-CHAN-001
# @trace: REQ-NRT-D

    state:       level_t, slope_t
    observation: log_price_t = level_t + noise

    "Use recursive filtering only. Smoother that uses future observations is
     forbidden for live-compatible features."

That prohibition is the whole design constraint. The Rauch-Tung-Striebel
smoother is the better estimator and every textbook reaches for it -- and it
runs backwards, so the state at bar 50 changes when bar 51 arrives. Every
feature derived from it repaints, which is PRD section 2.1's critical risk and
Test D's subject.

A comment cannot carry that claim. This module contains no backward pass and a
test asserts it over the source: no reversal, no `reversed`, no `smooth`.

The band comes from the innovation variance, as section 13.5 suggests: the
filter's own running surprise. A band that ignored it would be a fixed band with
extra arithmetic, and would not widen when the market stops behaving.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from channelflow.bars import Bar
from channelflow.channels.models import ChannelQuality, ChannelSnapshot
from channelflow.channels.window import fit_window

MODEL_NAME = "kalman_local_linear_trend"
MODEL_VERSION = "1.0.0"

NEGLIGIBLE_LOG_SPREAD = 1e-9


@dataclass(frozen=True)
class KalmanChannel:
    """A level-and-slope filter, run forward once."""

    lookback: int = 60
    #: Process noise on the level and the slope, in log-price units. Research
    #: defaults: they set how fast the filter follows a change, and PRD section
    #: 13.11's warning about research defaults applies to them too.
    level_noise: float = 1e-5
    slope_noise: float = 1e-7
    observation_noise: float = 1e-4
    #: How many innovation standard deviations the bands sit at. The normal 90th
    #: percentile, matching baseline A's default 0.10/0.90 pair.
    band_sigmas: float = 1.2816

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        window = fit_window(bars, as_of_ns=as_of_ns, lookback=self.lookback)
        log_prices = np.log(np.array([float(b.close) for b in window], dtype=np.float64))

        level, slope, covariance, innovations = _filter(
            log_prices,
            level_noise=self.level_noise,
            slope_noise=self.slope_noise,
            observation_noise=self.observation_noise,
        )

        # The filter's own running surprise, which is what section 13.5 means by
        # an adaptive band: it grows when the observations stop matching what
        # the state predicted.
        innovation_std = float(np.std(innovations)) if len(innovations) else 0.0
        band = self.band_sigmas * max(innovation_std, math.sqrt(self.observation_noise))

        center_now = math.exp(level)
        upper_now = math.exp(level + band)
        lower_now = math.exp(level - band)
        uncertainty = float(math.sqrt(max(covariance[0][0], 0.0)))

        return ChannelSnapshot(
            as_of_ns=as_of_ns,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            lookback=self.lookback,
            center_now=center_now,
            upper_now=upper_now,
            lower_now=lower_now,
            slope_normalized=(
                slope / innovation_std if innovation_std > NEGLIGIBLE_LOG_SPREAD else 0.0
            ),
            width_pct=(upper_now - lower_now) / center_now * 100.0 if center_now > 0 else 0.0,
            quality=ChannelQuality(
                # A filter that is certain of its level is a filter whose
                # observations have been agreeing with it.
                score=1.0 / (1.0 + uncertainty / max(innovation_std, NEGLIGIBLE_LOG_SPREAD)),
                submetrics={
                    "state_uncertainty": uncertainty,
                    "innovation_std": innovation_std,
                },
                contributing=("state_uncertainty", "innovation_std"),
                unavailable=("coverage_score", "touch_consistency"),
            ),
            source_max_event_time_ns=max(bar.close_time_ns for bar in window),
        )


def _filter(
    log_prices: np.ndarray, *, level_noise: float, slope_noise: float, observation_noise: float
) -> tuple[float, float, list[list[float]], list[float]]:
    """One forward pass. Each state sees its own observation and the ones before.

    Written as an explicit loop rather than with a matrix library's smoother,
    because the loop is the guarantee: there is nowhere in it that a later
    observation could enter.
    """
    level = float(log_prices[0])
    slope = 0.0
    # Start uncertain about both: a filter that begins confident takes the whole
    # window to admit it was wrong.
    covariance = [[1.0, 0.0], [0.0, 1.0]]
    innovations: list[float] = []

    for observation in log_prices[1:]:
        # Predict: the level moves by the slope, the slope stays.
        level = level + slope
        covariance = [
            [
                covariance[0][0]
                + covariance[0][1]
                + covariance[1][0]
                + covariance[1][1]
                + level_noise,
                covariance[0][1] + covariance[1][1],
            ],
            [covariance[1][0] + covariance[1][1], covariance[1][1] + slope_noise],
        ]

        # Update against this observation, and only this one.
        innovation = float(observation) - level
        innovation_variance = covariance[0][0] + observation_noise
        gain_level = covariance[0][0] / innovation_variance
        gain_slope = covariance[1][0] / innovation_variance

        level = level + gain_level * innovation
        slope = slope + gain_slope * innovation
        covariance = [
            [
                covariance[0][0] - gain_level * covariance[0][0],
                covariance[0][1] - gain_level * covariance[0][1],
            ],
            [
                covariance[1][0] - gain_slope * covariance[0][0],
                covariance[1][1] - gain_slope * covariance[0][1],
            ],
        ]
        innovations.append(innovation)

    return level, slope, covariance, innovations
