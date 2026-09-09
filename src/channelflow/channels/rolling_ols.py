"""Baseline A: rolling OLS on log price (PRD section 13.2).

# @trace: REQ-WP-006

The filtering comes before the fitting, deliberately. PRD section 13.1 states
the invariant `source_max_event_time <= as_of`, section 2.1 calls repainting the
critical risk the product exists to avoid, and Constitution Principle I adds
that the rule holds "even when violating it would improve a backtest". A channel
fitted with hindsight looks superb, which is exactly why the guard cannot be the
caller's responsibility.

So `fit` takes the whole history and an `as_of`, and does the filtering itself.
A caller who passes future bars gets the same answer as one who does not.

**On float64.** The fit is least squares in log space -- inherently
floating-point. Using `Decimal` here would be theatre: `log` and `exp` are not
exact operations, and the precision would be lost at the first transcendental
call regardless. Prices arrive as `Decimal` and are converted once, at the
boundary, where the conversion is visible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from channelflow.bars import Bar
from channelflow.channels.models import ChannelSnapshot
from channelflow.channels.quality import score_channel
from channelflow.channels.window import fit_window

MODEL_NAME = "rolling_ols_log_price"
MODEL_VERSION = "1.0.0"

#: Residual spread below which there is no measurable noise, so a
#: signal-to-noise ratio has nothing to divide by. See the use site.
NEGLIGIBLE_LOG_SPREAD = 1e-9


@dataclass(frozen=True)
class RollingOLSChannel:
    """Fit a log-linear channel over the most recent `lookback` finalized bars."""

    lookback: int = 60
    quantile_low: float = 0.10
    quantile_high: float = 0.90
    weights: dict[str, float] | None = None

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot:
        window = self._window(bars, as_of_ns=as_of_ns)
        closes = np.array([float(bar.close) for bar in window], dtype=np.float64)

        log_prices = np.log(closes)
        index = np.arange(len(window), dtype=np.float64)
        slope, intercept = np.polyfit(index, log_prices, 1)

        fitted = intercept + slope * index
        residuals = log_prices - fitted

        low_q = float(np.quantile(residuals, self.quantile_low))
        high_q = float(np.quantile(residuals, self.quantile_high))

        center_log_now = float(fitted[-1])
        center_now = math.exp(center_log_now)
        upper_now = math.exp(center_log_now + high_q)
        lower_now = math.exp(center_log_now + low_q)

        # ADR-007: slope in units of its own noise, so the value is comparable
        # between a symbol at 78,000 and one at 0.4 -- which is what ranking
        # many markets actually asks.
        # Below this, the residual spread is floating-point dust from the fit
        # rather than market noise. Dividing by it produced a slope_normalized
        # of 0.088 on a perfectly flat series -- a reported trend that does not
        # exist. Log prices are O(1) to O(12), so 1e-9 in log space is far below
        # any real price movement and far above the fit's own rounding.
        residual_std = float(np.std(residuals))
        slope_normalized = (
            float(slope / residual_std) if residual_std > NEGLIGIBLE_LOG_SPREAD else 0.0
        )

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
                low=low_q,
                high=high_q,
                target_coverage=self.quantile_high - self.quantile_low,
                weights=self.weights,
            ),
            source_max_event_time_ns=max(bar.close_time_ns for bar in window),
        )

    def _window(self, bars: list[Bar], *, as_of_ns: int) -> list[Bar]:
        return fit_window(bars, as_of_ns=as_of_ns, lookback=self.lookback)
