"""PRD section 13A.5's reversal thresholds.

# @trace: REQ-WP-019

    FIXED_BPS
    ATR_MULTIPLE
    REALIZED_VOL_MULTIPLE
    CHANNEL_WIDTH_FRACTION
    HYBRID

and the example the PRD gives for the adaptive one:

    theta_t = max(min_bps, atr_multiplier * ATR_t / price_t,
                  vol_multiplier * realized_vol_t)

Section 13A.5 closes with the rule that matters most here: "The threshold must
be point-in-time and cannot be retroactively optimized per swing." So every
computation below takes the bars available at `t` and nothing else, and the
value in force at a confirmation is stored on the record rather than recomputed
when someone wants to look at it again.

Section 13A.29's second named failure mode is a fixed threshold failing across
volatility regimes, which is why the fixed mode exists but is not the default
anyone should reach for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from channelflow.bars import Bar

BPS = 10_000.0


class ThresholdMode(StrEnum):
    FIXED_BPS = "FIXED_BPS"
    ATR_MULTIPLE = "ATR_MULTIPLE"
    REALIZED_VOL_MULTIPLE = "REALIZED_VOL_MULTIPLE"
    CHANNEL_WIDTH_FRACTION = "CHANNEL_WIDTH_FRACTION"
    HYBRID = "HYBRID"


class ThresholdUnavailable(ValueError):
    """Not enough history to compute the threshold, and the reason is named.

    Raised rather than falling back to the floor: a threshold computed over
    fewer bars than configured is a different threshold wearing the same name,
    and a confirmation resting on it could not be reproduced.
    """


@dataclass(frozen=True)
class ThresholdPolicy:
    """How far price must reverse. Every value is an argument.

    PRD section 13A.27: "Config values above are research defaults and must not
    be treated as optimized constants."
    """

    mode: ThresholdMode = ThresholdMode.HYBRID
    min_bps: float = 50.0
    atr_multiplier: float = 1.5
    atr_period: int = 14
    vol_multiplier: float = 2.0
    vol_period: int = 20
    channel_width_fraction: float = 0.25

    def at(
        self,
        bars: list[Bar],
        *,
        as_of_ns: int,
        channel_width_pct: float | None = None,
    ) -> float:
        """The threshold in basis points, from data at or before `as_of_ns`.

        The filtering happens here rather than in the caller for the same
        reason REQ-WP-006's fitter filters its own window: a caller who passes
        later bars must get the same answer as one who does not.
        """
        window = [b for b in bars if b.close_time_ns <= as_of_ns]
        if not window:
            raise ThresholdUnavailable(f"no bars at or before {as_of_ns}")

        if self.mode is ThresholdMode.FIXED_BPS:
            return self.min_bps
        if self.mode is ThresholdMode.ATR_MULTIPLE:
            return self._atr_bps(window)
        if self.mode is ThresholdMode.REALIZED_VOL_MULTIPLE:
            return self._vol_bps(window)
        if self.mode is ThresholdMode.CHANNEL_WIDTH_FRACTION:
            return self._channel_bps(channel_width_pct)

        # HYBRID: the PRD's own formula, a maximum over the components. The
        # floor is part of the maximum, so the hybrid is never below it.
        components = [self.min_bps]
        for component in (self._atr_bps, self._vol_bps):
            try:
                components.append(component(window))
            except ThresholdUnavailable:
                # A component without enough history contributes nothing rather
                # than failing the whole policy -- the floor still applies, and
                # the alternative is no threshold at all early in a stream.
                continue
        if channel_width_pct is not None:
            components.append(self._channel_bps(channel_width_pct))
        return max(components)

    def _atr_bps(self, window: list[Bar]) -> float:
        if len(window) < self.atr_period + 1:
            raise ThresholdUnavailable(f"ATR needs {self.atr_period + 1} bars, found {len(window)}")
        recent = window[-(self.atr_period + 1) :]
        ranges = [
            max(
                float(current.high - current.low),
                abs(float(current.high) - float(previous.close)),
                abs(float(current.low) - float(previous.close)),
            )
            for previous, current in zip(recent[:-1], recent[1:], strict=True)
        ]
        atr = sum(ranges) / len(ranges)
        price = float(window[-1].close)
        return self.atr_multiplier * atr / price * BPS

    def _vol_bps(self, window: list[Bar]) -> float:
        if len(window) < self.vol_period + 1:
            raise ThresholdUnavailable(
                f"realized volatility needs {self.vol_period + 1} bars, found {len(window)}"
            )
        recent = window[-(self.vol_period + 1) :]
        returns = [
            math.log(float(current.close) / float(previous.close))
            for previous, current in zip(recent[:-1], recent[1:], strict=True)
        ]
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return self.vol_multiplier * math.sqrt(variance) * BPS

    def _channel_bps(self, channel_width_pct: float | None) -> float:
        """A fraction of the channel's width, in basis points.

        `channel_width_pct` is a percentage, in the same units as
        `ChannelSnapshot.width_pct` -- which is where every caller gets it. It
        used to be read as a fraction of price, and the two differ by a hundred:
        a real 2% channel passed straight through came out as a 5,000 bps
        threshold, the detector confirmed nothing for the rest of the series,
        and the report read "this method found no extrema".
        """
        if channel_width_pct is None:
            raise ThresholdUnavailable(
                "CHANNEL_WIDTH_FRACTION needs a channel width; none was supplied"
            )
        return self.channel_width_fraction * (channel_width_pct / 100.0) * BPS
