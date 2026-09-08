"""Signed trade notional and cumulative volume delta (PRD section 15.4).

# @trace: REQ-WP-011

    delta_t = aggressive_buy_notional - aggressive_sell_notional
    CVD_t   = CVD_{t-1} + delta_t

Notional rather than base quantity, because the PRD says notional and
`TradeEvent` carries `notional_quote` directly. Nothing here approximates it by
multiplying size by a price -- the approximation would be invisible in the
output and wrong whenever price moved inside a bar.

Section 15.4 lists five features; this builds four. CVD-price divergence is
named there without a formula, and sign disagreement, normalized slope
difference, correlation breakdown and swing divergence give four different
numbers under one name. ADR-013 is the record of why it waits for a definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.domain import TradeEvent
from channelflow.features.registry import FeatureSpec, register

SECOND_NS = 1_000_000_000

FEATURES: tuple[str, ...] = (
    "delta_notional",
    "cvd",
    "cvd_slope",
    "cvd_acceleration",
    "normalized_delta",
)


@dataclass(frozen=True)
class FlowWindow:
    """What traded in a span of event time, and which way it leaned."""

    delta: Decimal
    volume: Decimal
    trades: int
    window_ns: int
    as_of_ns: int
    cvd_start: Decimal
    cvd_end: Decimal

    @property
    def normalized_delta(self) -> float | None:
        """Delta as a fraction of the window's notional -- or nothing.

        None rather than 0.0 when nothing traded (FR-012). Zero means the buys
        and the sells cancelled; None means there were none. A caller reading a
        silent minute as perfectly balanced is acting on a fact that did not
        happen.
        """
        if self.volume == 0:
            return None
        return float(self.delta / self.volume)

    @property
    def cvd_slope_per_second(self) -> float:
        """How fast cumulative delta moved across the window."""
        if self.window_ns == 0:
            return 0.0
        return float(self.cvd_end - self.cvd_start) / (self.window_ns / SECOND_NS)


@dataclass
class FlowTracker:
    """Trades in, delta and cumulative delta out."""

    cumulative_delta: Decimal = Decimal(0)
    _last_event_time_ns: int = 0
    #: (event_time, delta, notional) per trade, and the running CVD after it.
    _history: list[tuple[int, Decimal, Decimal, Decimal]] = field(default_factory=list)

    def observe(self, event: TradeEvent) -> Decimal:
        """Record one trade. Returns cumulative delta after it."""
        if event.meta.event_time_ns < self._last_event_time_ns:
            raise ValueError(
                "trades must arrive in event-time order; "
                f"{event.meta.event_time_ns} follows {self._last_event_time_ns}. "
                "A cumulative total that has already been read cannot be rewritten "
                "by a late arrival (Principle III)"
            )

        # An unknown aggressor is not a zero-sized trade. It moved volume and we
        # do not know which way -- dropping it understates volume, guessing a
        # side invents flow, and both errors are invisible downstream.
        if event.aggressor_side == "buy":
            delta = event.notional_quote
        elif event.aggressor_side == "sell":
            delta = -event.notional_quote
        else:
            delta = Decimal(0)

        self.cumulative_delta += delta
        self._last_event_time_ns = event.meta.event_time_ns
        self._history.append(
            (event.meta.event_time_ns, delta, event.notional_quote, self.cumulative_delta)
        )
        return self.cumulative_delta

    def window(self, window_ns: int, *, as_of_ns: int) -> FlowWindow:
        """Everything in `(as_of_ns - window_ns, as_of_ns]`."""
        floor = as_of_ns - window_ns
        inside = [row for row in self._history if floor < row[0] <= as_of_ns]
        return FlowWindow(
            delta=sum((row[1] for row in inside), Decimal(0)),
            volume=sum((row[2] for row in inside), Decimal(0)),
            trades=len(inside),
            window_ns=window_ns,
            as_of_ns=as_of_ns,
            cvd_start=self._cvd_at(floor),
            cvd_end=self._cvd_at(as_of_ns),
        )

    def acceleration(self, window_ns: int, *, as_of_ns: int) -> float:
        """Change in CVD slope between this window and the one before it."""
        current = self.window(window_ns, as_of_ns=as_of_ns)
        previous = self.window(window_ns, as_of_ns=as_of_ns - window_ns)
        seconds = window_ns / SECOND_NS
        return (current.cvd_slope_per_second - previous.cvd_slope_per_second) / seconds

    def _cvd_at(self, event_time_ns: int) -> Decimal:
        """Cumulative delta as of an event time -- the last value at or before it."""
        result = Decimal(0)
        for time_ns, _, _, cvd in self._history:
            if time_ns > event_time_ns:
                break
            result = cvd
        return result


def _register_all() -> None:
    common = {
        "family": "trade_flow",
        "source_events": ("trade",),
        "availability_lag_ms": 0,
        "clipping": "none",
        "point_in_time_safe": True,
    }
    register(
        FeatureSpec(
            name="delta_notional",
            version=1,
            description="Signed aggressive notional over a window.",
            formula="aggressive_buy_notional - aggressive_sell_notional; "
            "trades of unknown aggressor contribute to volume and to neither side",
            unit="quote currency",
            lookback="window length, caller supplied",
            cadence="per trade",
            null_policy="zero when no trades; the trade count distinguishes it",
            normalization="none; see normalized_delta",
            test_fixture=(
                "tests/unit/features/test_flow.py::test_delta_is_buy_notional_minus_sell_notional"
            ),
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd",
            version=1,
            description="Cumulative volume delta: the running sum of signed notional.",
            formula="CVD_t = CVD_{t-1} + delta_t",
            unit="quote currency",
            lookback="since the tracker started",
            cadence="per trade",
            null_policy="starts at zero; never null",
            normalization="none; an unbounded running total",
            test_fixture="tests/unit/features/test_flow.py::test_cumulative_delta_is_the_running_sum",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd_slope",
            version=1,
            description="Rate of change of cumulative volume delta across a window.",
            formula="(CVD at window end - CVD at window start) / window seconds",
            unit="quote currency per second",
            lookback="window length, caller supplied",
            cadence="per trade",
            null_policy="zero for a zero-length window",
            normalization="none; per-second rate",
            test_fixture=(
                "tests/unit/features/test_flow.py"
                "::test_the_cvd_slope_is_the_change_across_the_window_per_second"
            ),
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="cvd_acceleration",
            version=1,
            description="Change in CVD slope between a window and the one before it.",
            formula="(slope of current window - slope of previous window) / window seconds",
            unit="quote currency per second squared",
            lookback="two window lengths",
            cadence="per trade",
            null_policy="zero when both windows are empty",
            normalization="none",
            test_fixture=(
                "tests/unit/features/test_flow.py"
                "::test_acceleration_compares_a_window_with_the_one_before_it"
            ),
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="normalized_delta",
            version=1,
            description="Signed notional as a fraction of the window's total notional.",
            formula="delta_notional / total_notional",
            unit="normalized",
            lookback="window length, caller supplied",
            cadence="per trade",
            null_policy=(
                "absent when the window has no volume; zero would read as balanced "
                "flow where there was none"
            ),
            normalization="divided by the window's own volume, so comparable across symbols",
            test_fixture=(
                "tests/unit/features/test_flow.py"
                "::test_normalized_delta_is_delta_over_the_window_volume"
            ),
            **common,  # type: ignore[arg-type]
        )
    )


_register_all()
