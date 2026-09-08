"""Channel quality submetrics (PRD section 13.9).

# @trace: REQ-WP-006

Each submetric states what it measures and in what units, because a score in
[0,1] assembled from unnamed parts is a number nobody can argue with -- and
Constitution Principle VI requires a feature to declare its semantics.

Six of PRD section 13.9's nine are computable here. The other three are omitted
rather than defaulted; ADR-007 explains why.

None of these weights is a finding. PRD section 48 lists the research questions
that must be answered before any of this drives a decision, and section 13.9
says ML scoring replaces the transparent average later. This is a starting point
for measurement.
"""

from __future__ import annotations

import numpy as np

from channelflow.channels.models import ChannelQuality

#: PRD section 13.9 asks for a transparent weighted average. Configurable per
#: PRD section 0.12; equal weights are a deliberate refusal to pretend we know
#: which submetric matters more before anything has been measured.
DEFAULT_WEIGHTS: dict[str, float] = {
    "coverage_score": 1.0,
    "touch_consistency": 1.0,
    "slope_stability": 1.0,
    "width_stability": 1.0,
    "residual_structure_penalty": 1.0,
    "outlier_penalty": 1.0,
}

#: Named so the snapshot can say what it could not compute, rather than leaving
#: a reader to infer it from a short list.
UNAVAILABLE = (
    "forecast_calibration_score",  # needs PRD section 13.8's forecast channel
    "regime_compatibility",  # needs PRD section 20's regime engine
    "age_score",  # needs channel-lifetime tracking nothing keeps yet
)


def coverage_score(residuals: np.ndarray, low: float, high: float, target: float) -> float:
    """Fraction of closes inside the band, scored against the band's own width.

    Unit: 1.0 when the observed coverage equals what the quantile levels imply,
    falling linearly with the discrepancy. A channel containing far more or far
    less than it promises is describing something other than the data.
    """
    inside = float(np.mean((residuals >= low) & (residuals <= high)))
    return max(0.0, 1.0 - abs(inside - target) / max(target, 1e-9))


def touch_consistency(residuals: np.ndarray, low: float, high: float) -> float:
    """How regularly price interacts with the boundaries.

    Unit: 1.0 when roughly a fifth of closes sit in the outer tenth of the band
    on either side. A channel price never approaches is too wide to say
    anything; one it sits outside of is not containing it.
    """
    span = high - low
    if span <= 0:
        return 0.0
    near_edge = float(np.mean((residuals <= low + 0.1 * span) | (residuals >= high - 0.1 * span)))
    return max(0.0, 1.0 - abs(near_edge - 0.2) / 0.2)


def slope_stability(log_prices: np.ndarray, window: int = 10) -> float:
    """How steady the trend direction is across sub-windows.

    Unit: 1.0 when every sub-window agrees on direction, 0.0 when they alternate.
    PRD section 13.9 asks to penalise "violent sign flipping".
    """
    if len(log_prices) < window * 2:
        return 0.0
    slopes = [
        float(np.polyfit(np.arange(window), log_prices[i : i + window], 1)[0])
        for i in range(0, len(log_prices) - window, window)
    ]
    if len(slopes) < 2:
        return 0.0
    signs = np.sign(slopes)
    flips = float(np.mean(signs[1:] != signs[:-1]))
    return max(0.0, 1.0 - flips)


def width_stability(residuals: np.ndarray, window: int = 20) -> float:
    """How steady the residual spread is.

    Unit: 1.0 when sub-window spreads are identical; falls with their relative
    variation. A band whose width lurches is describing a changing process.
    """
    if len(residuals) < window * 2:
        return 0.0
    spreads = [
        float(np.std(residuals[i : i + window])) for i in range(0, len(residuals) - window, window)
    ]
    mean_spread = float(np.mean(spreads))
    if mean_spread <= 0:
        return 1.0
    return max(0.0, 1.0 - float(np.std(spreads)) / mean_spread)


def residual_structure_penalty(residuals: np.ndarray) -> float:
    """Whether residuals still carry trend the line failed to capture.

    Unit: 1.0 when successive residuals are uncorrelated, falling toward 0.0 as
    autocorrelation rises. Strong structure means the model is wrong, not that
    the market is trending.
    """
    if len(residuals) < 3:
        return 0.0
    centred = residuals - float(np.mean(residuals))
    denominator = float(np.sum(centred**2))
    if denominator <= 0:
        return 1.0
    lag1 = float(np.sum(centred[1:] * centred[:-1])) / denominator
    return max(0.0, 1.0 - abs(lag1))


def outlier_penalty(residuals: np.ndarray) -> float:
    """How much of the fit is driven by a few extreme points.

    Unit: 1.0 when no residual exceeds four robust deviations, falling as
    outliers accumulate. A line pinned by three spikes is not a channel.
    """
    if len(residuals) < 3:
        return 0.0
    median = float(np.median(residuals))
    mad = float(np.median(np.abs(residuals - median)))
    if mad <= 0:
        return 1.0
    extreme = float(np.mean(np.abs(residuals - median) / (1.4826 * mad) > 4.0))
    return max(0.0, 1.0 - extreme * 5.0)


def score_channel(
    *,
    residuals: np.ndarray,
    log_prices: np.ndarray,
    low: float,
    high: float,
    target_coverage: float,
    weights: dict[str, float] | None = None,
) -> ChannelQuality:
    """Combine the computable submetrics into a transparent weighted average."""
    weights = weights or DEFAULT_WEIGHTS
    submetrics = {
        "coverage_score": coverage_score(residuals, low, high, target_coverage),
        "touch_consistency": touch_consistency(residuals, low, high),
        "slope_stability": slope_stability(log_prices),
        "width_stability": width_stability(residuals),
        "residual_structure_penalty": residual_structure_penalty(residuals),
        "outlier_penalty": outlier_penalty(residuals),
    }
    contributing = tuple(sorted(k for k in submetrics if k in weights))
    total_weight = sum(weights[k] for k in contributing)
    score = (
        sum(submetrics[k] * weights[k] for k in contributing) / total_weight
        if total_weight > 0
        else 0.0
    )
    return ChannelQuality(
        score=min(1.0, max(0.0, score)),
        submetrics=submetrics,
        contributing=contributing,
        unavailable=UNAVAILABLE,
    )
