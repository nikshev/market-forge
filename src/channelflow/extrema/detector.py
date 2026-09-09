"""PRD section 13A.5's directional-change baseline.

# @trace: REQ-WP-019
# @trace: REQ-EXP-011
# @trace: REQ-NRT-A
# @trace: REQ-NRT-C
# @trace: REQ-NRT-E

"Maintain a running high during an upswing and a running low during a
downswing. A high becomes confirmed only after price reverses by a threshold
`theta` from that running high."

That sentence is the whole engine, and section 13A.1 is why it matters: the
high happened at `extremum_time`, and the system could not legally know it
until `known_at`, when the reversal crossed the threshold. The gap between them
is the confirmation lag, and a backtest acting on the label before `known_at`
is invalid.

Nothing here looks forward. The detector sees one bar at a time and emits at
most one confirmation per bar; a bar appended later cannot change a
confirmation already emitted, because the emission depended only on bars up to
its own `known_at`. That is Test A, and it holds by construction rather than by
care.

There is no clock. Every timestamp is a bar's own event time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from channelflow.bars import Bar
from channelflow.extrema.models import (
    CandidateInvalidation,
    ConfirmedExtremum,
    ExtremumCandidate,
)
from channelflow.extrema.prominence import ProminenceRule, prominence_bps
from channelflow.extrema.thresholds import ThresholdPolicy, ThresholdUnavailable

METHOD = "directional_change"
BPS = 10_000.0

Direction = Literal["UP", "DOWN"]


@dataclass
class DirectionalChangeDetector:
    """One instrument, one timeframe, one direction at a time.

    Every threshold and filter is an argument (Principle X, PRD section
    13A.27). The defaults are research defaults and are not optimized
    constants.
    """

    instrument_id: str = "BTCUSDT"
    venue_scope: str = "binance"
    thresholds: ThresholdPolicy = field(default_factory=ThresholdPolicy)
    prominence: ProminenceRule = field(default_factory=ProminenceRule)

    #: Everything emitted, in order. Append-only: PRD section 13A.2's lifecycle
    #: and Test B both require that a record, once made, is never edited.
    candidates: list[ExtremumCandidate] = field(default_factory=list)
    confirmed: list[ConfirmedExtremum] = field(default_factory=list)
    invalidations: list[CandidateInvalidation] = field(default_factory=list)

    _direction: Direction | None = None
    #: While the direction is undetermined both extremes are tracked. The swing
    #: that led into the first bar was never observed, so neither of them can be
    #: confirmed -- see `_settle_direction`.
    _running_high: tuple[float, int, int] | None = None
    _running_low: tuple[float, int, int] | None = None
    _extreme_price: float | None = None
    _extreme_time_ns: int | None = None
    _extreme_index: int | None = None
    _swing_start_price: float | None = None
    _last_confirmed_index: int | None = None
    _seen: list[Bar] = field(default_factory=list)

    def on_bar(
        self, bar: Bar, *, channel_width_pct: float | None = None
    ) -> ConfirmedExtremum | None:
        """Advance by one bar. Returns a confirmation, or None.

        `channel_width_pct` is what PRD section 13A.5's `CHANNEL_WIDTH_FRACTION`
        threshold needs, and the caller has it: the detector holds bars and the
        channel is fitted elsewhere. Without it that mode raises rather than
        falling back to another -- a threshold silently computed a different way
        is a different detector under the same name.

        The bar is appended to the detector's own history before anything is
        computed, and every computation reads only that history -- so a later
        bar cannot participate in this bar's decision.
        """
        self._seen.append(bar)
        index = len(self._seen) - 1
        close = float(bar.close)

        if self._direction is None:
            self._settle_direction(close, bar, index, channel_width_pct)
            return None

        if self._direction == "UP":
            if close >= (self._extreme_price or close):
                self._extend(close, bar, index, "HIGH")
                return None
            return self._maybe_confirm(bar, index, close, "HIGH", channel_width_pct)

        if close <= (self._extreme_price or close):
            self._extend(close, bar, index, "LOW")
            return None
        return self._maybe_confirm(bar, index, close, "LOW", channel_width_pct)

    def run(self, bars: list[Bar]) -> list[ConfirmedExtremum]:
        """Feed a whole series. Returns what was confirmed, in order."""
        for bar in bars:
            self.on_bar(bar)
        return list(self.confirmed)

    # --- internals ---

    def _settle_direction(
        self, close: float, bar: Bar, index: int, channel_width_pct: float | None = None
    ) -> None:
        """Find out which way the market was going before we started watching.

        The swing that produced the first bar was never observed, so the
        extreme it ended at cannot be confirmed -- we have no idea whether it
        was a turning point or a step on the way. Assuming a direction and
        confirming from it reports an extremum from a swing nobody saw, which
        is the first thing the spec's edge cases forbid.

        So both extremes are tracked until price moves a full threshold away
        from one of them. That move settles the direction, and the extreme it
        moved away from is discarded rather than emitted.
        """
        here = (close, bar.close_time_ns, index)
        if self._running_high is None or close >= self._running_high[0]:
            self._running_high = here
        if self._running_low is None or close <= self._running_low[0]:
            self._running_low = here

        try:
            threshold = self.thresholds.at(
                self._seen,
                as_of_ns=bar.close_time_ns,
                channel_width_pct=channel_width_pct,
            )
        except ThresholdUnavailable:
            return

        high_price = self._running_high[0]
        low_price = self._running_low[0]
        fell = (high_price - close) / high_price * BPS
        rose = (close - low_price) / low_price * BPS

        if fell >= threshold:
            self._direction = "DOWN"
            self._swing_start_price = high_price
        elif rose >= threshold:
            self._direction = "UP"
            self._swing_start_price = low_price
        else:
            return

        self._extreme_price = close
        self._extreme_time_ns = bar.close_time_ns
        self._extreme_index = index

    def _extend(self, close: float, bar: Bar, index: int, kind: str) -> None:
        """A new running extreme. Recorded as a candidate, observed now."""
        self._extreme_price = close
        self._extreme_time_ns = bar.close_time_ns
        self._extreme_index = index
        self.candidates.append(
            ExtremumCandidate.create(
                instrument_id=self.instrument_id,
                venue_scope=self.venue_scope,
                timeframe_ns=bar.timeframe_ns,
                candidate_type=kind,  # type: ignore[arg-type]
                candidate_time_ns=bar.close_time_ns,
                observed_at_ns=bar.close_time_ns,
                price=bar.close,
                method=METHOD,
                structural_score=0.0,
            )
        )

    def _maybe_confirm(
        self,
        bar: Bar,
        index: int,
        close: float,
        kind: str,
        channel_width_pct: float | None = None,
    ) -> ConfirmedExtremum | None:
        extreme = self._extreme_price
        extreme_time = self._extreme_time_ns
        extreme_index = self._extreme_index
        if extreme is None or extreme_time is None or extreme_index is None:
            return None

        reversal = abs(close - extreme) / extreme * BPS
        try:
            threshold = self.thresholds.at(
                self._seen,
                as_of_ns=bar.close_time_ns,
                channel_width_pct=channel_width_pct,
            )
        except ThresholdUnavailable:
            # No threshold, no confirmation. Approximating one would produce a
            # confirmation nobody could reproduce.
            return None
        if reversal < threshold:
            return None

        baseline = self._swing_start_price or extreme
        prom_bps = prominence_bps(extreme, baseline)
        bars_since = (
            None
            if self._last_confirmed_index is None
            else extreme_index - self._last_confirmed_index
        )
        if not self.prominence.accepts(
            prominence_bps=prom_bps, prominence_atr=None, bars_since_previous=bars_since
        ):
            # Too small or too soon. The swing still turns -- the detector
            # flips direction -- but nothing is reported (PRD section 13A.29's
            # first failure mode).
            self._flip(close, bar, index)
            return None

        confirmation = ConfirmedExtremum.create(
            instrument_id=self.instrument_id,
            timeframe_ns=bar.timeframe_ns,
            extremum_type=kind,
            extremum_time_ns=extreme_time,
            known_at_ns=bar.close_time_ns,
            price=Decimal(str(extreme)),
            confirmation_method=METHOD,
            confirmation_lag_bars=index - extreme_index,
            reversal_bps=reversal,
            threshold_bps=threshold,
            prominence_bps=prom_bps,
        )
        self.confirmed.append(confirmation)
        self._last_confirmed_index = extreme_index
        self._flip(close, bar, index)
        return confirmation

    def _flip(self, close: float, bar: Bar, index: int) -> None:
        self._direction = "DOWN" if self._direction == "UP" else "UP"
        self._swing_start_price = self._extreme_price
        self._extreme_price = close
        self._extreme_time_ns = bar.close_time_ns
        self._extreme_index = index
