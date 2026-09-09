"""EXP-011: which non-repainting swing detector is worth using.

# @trace: REQ-EXP-011

    Compare non-repainting confirmed swing methods: fixed-bps directional
    change; ATR-adaptive; realized-vol adaptive; channel-width adaptive; hybrid
    threshold.

    Metrics: confirmation lag; extrema per 1000 bars; prominence; stability
    across volatility regimes; downstream setup expectancy.

The five methods are [[REQ-WP-019]]'s five `ThresholdMode` values, run through
the production detector. A comparison that reimplemented the lifecycle would be
comparing its own copy, and the lifecycle is where the non-repainting guarantee
lives.

The five metrics pull against each other, which is the point. A detector that
confirms quickly confirms more and confirms noise; one that waits for prominence
confirms little and confirms late. There is no single winner, so the report
ranks nothing and states all five side by side -- the choice is the reader's and
depends on what they are building.

**Stability across volatility regimes** is the metric that decides most real
arguments. A fixed threshold in basis points finds a swing every other bar in a
storm and nothing at all in a drift; an adaptive one is supposed not to. The
regimes are split by realized volatility, and the report carries each regime's
rate rather than only the spread, so a reader sees which way it failed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median

import numpy as np

from channelflow.backtest import (
    CostModel,
    CostsRequired,
    EconomicReport,
    HorizonUnavailable,
    NoFillAvailable,
    Outcome,
    economic_report,
    market_at_next_open,
    resolve_outcome,
)
from channelflow.bars import Bar
from channelflow.channels import ChannelFitError, ChannelModel
from channelflow.extrema import (
    ConfirmedExtremum,
    DirectionalChangeDetector,
    ThresholdMode,
    ThresholdPolicy,
    ThresholdUnavailable,
)

#: EXP-011's five, which are the threshold policy's five modes.
METHODS: tuple[ThresholdMode, ...] = tuple(ThresholdMode)

BARS_PER_RATE = 1000


@dataclass(frozen=True)
class RegimeRate:
    """How often a detector fired in one volatility regime."""

    label: str
    bars: int
    extrema: int

    @property
    def per_1000_bars(self) -> float:
        return self.extrema / self.bars * BARS_PER_RATE if self.bars else 0.0


@dataclass(frozen=True)
class DetectorEntry:
    """One method's five metrics, or why it has none."""

    method: ThresholdMode
    extrema: int = 0
    per_1000_bars: float = 0.0
    median_lag_bars: float | None = None
    median_prominence_bps: float | None = None
    regimes: tuple[RegimeRate, ...] = ()
    #: The ratio of the busier regime's rate to the quieter one's. One means a
    #: detector that fires at the same rate whatever the market is doing, which
    #: is what "adaptive" claims.
    regime_ratio: float | None = None
    trades: int = 0
    expectancy: EconomicReport | None = None
    reason: str = ""


@dataclass(frozen=True)
class DetectorComparison:
    """Every method, and what they all shared."""

    entries: dict[ThresholdMode, DetectorEntry]
    bars: int
    costs: CostModel
    note: str = (
        "the five metrics pull against each other: a detector that confirms sooner "
        "confirms more and confirms noise. Nothing is ranked -- the choice depends "
        "on what is being built"
    )


def compare_detectors(
    bars: list[Bar],
    *,
    costs: CostModel | None,
    methods: Sequence[ThresholdMode] = METHODS,
    policy: ThresholdPolicy | None = None,
    channel: ChannelModel | None = None,
    horizon_bars: int = 10,
    risk_per_trade: float = 0.02,
) -> DetectorComparison:
    """Run every method over one series and report EXP-011's five metrics.

    `channel` is fitted only for `CHANNEL_WIDTH_FRACTION`, which needs a width
    the detector cannot compute for itself. Without one that method is reported
    as unavailable rather than as a method that found nothing -- the two look
    identical in a count of zero and mean opposite things.
    """
    if costs is None:
        raise CostsRequired(
            "downstream setup expectancy is one of EXP-011's five metrics, and PRD "
            "section 41 rule 9 governs it"
        )

    base = policy or ThresholdPolicy()
    labels = volatility_regime(bars)
    entries: dict[ThresholdMode, DetectorEntry] = {}

    widths = (
        _channel_widths(bars, channel) if ThresholdMode.CHANNEL_WIDTH_FRACTION in methods else {}
    )

    for method in methods:
        if method is ThresholdMode.CHANNEL_WIDTH_FRACTION and not widths:
            entries[method] = DetectorEntry(
                method=method,
                reason=(
                    "this mode needs a channel width and no channel model was supplied; "
                    "a count of zero here would read as a method that found nothing"
                ),
            )
            continue

        detector = DirectionalChangeDetector(
            thresholds=ThresholdPolicy(**{**vars(base), "mode": method})
        )
        confirmed: list[ConfirmedExtremum] = []
        for index, bar in enumerate(bars):
            try:
                found = detector.on_bar(bar, channel_width_pct=widths.get(index))
            except ThresholdUnavailable:
                # Not enough history yet for this mode's threshold. A fact about
                # the warm-up, not about the method.
                continue
            if found is not None:
                confirmed.append(found)

        if not confirmed:
            entries[method] = DetectorEntry(
                method=method, reason="no extremum was confirmed over this series"
            )
            continue

        expectancy, trades = _expectancy(
            confirmed,
            bars,
            costs=costs,
            horizon_bars=horizon_bars,
            risk_per_trade=risk_per_trade,
        )
        prominences = [e.prominence_bps for e in confirmed if e.prominence_bps is not None]
        rates = _rates(confirmed, bars, labels)
        entries[method] = DetectorEntry(
            method=method,
            extrema=len(confirmed),
            per_1000_bars=len(confirmed) / len(bars) * BARS_PER_RATE,
            median_lag_bars=median(e.confirmation_lag_bars for e in confirmed),
            median_prominence_bps=median(prominences) if prominences else None,
            regimes=rates,
            regime_ratio=_ratio(rates),
            trades=trades,
            expectancy=expectancy,
        )

    return DetectorComparison(entries=entries, bars=len(bars), costs=costs)


def volatility_regime(bars: list[Bar]) -> tuple[str, ...]:
    """One label per bar: "calm" or "volatile", split at the series' own median.

    At the median rather than into fixed halves: a series whose second half is
    quieter would otherwise have its "volatile" regime be the calm one, and the
    stability metric would report the opposite of what happened.

    Public because it is the metric's definition. A reader who disagrees with
    how a regime is drawn should be able to see it drawn.
    """
    if len(bars) < 4:
        return ()
    closes = np.array([float(b.close) for b in bars])
    log_prices = np.log(closes)
    returns = np.abs(np.diff(log_prices, prepend=log_prices[0]))
    window = max(len(bars) // 20, 2)
    rolling = np.convolve(returns, np.ones(window) / window, mode="same")
    cut = float(np.median(rolling))
    return tuple("volatile" if value > cut else "calm" for value in rolling)


def _rates(
    confirmed: Sequence[ConfirmedExtremum],
    bars: list[Bar],
    labels: Sequence[str],
) -> tuple[RegimeRate, ...]:
    """How many extrema were confirmed in each regime, and over how many bars.

    An extremum belongs to the regime of the bar it was *confirmed* on, not of
    the bar it happened on. The confirmation is what a live system would have
    acted on, and the two can sit in different regimes -- which is exactly what
    a detector that lags into a storm looks like.
    """
    if not labels:
        return ()
    by_time = {bar.close_time_ns: index for index, bar in enumerate(bars)}
    counted = {"calm": 0, "volatile": 0}
    for extremum in confirmed:
        index = by_time.get(extremum.known_at_ns)
        if index is None or index >= len(labels):
            continue
        counted[labels[index]] += 1
    return tuple(
        RegimeRate(
            label=label,
            bars=sum(1 for value in labels if value == label),
            extrema=counted[label],
        )
        for label in ("calm", "volatile")
    )


def _ratio(rates: Sequence[RegimeRate]) -> float | None:
    """The busier regime's rate over the quieter one's."""
    if len(rates) != 2:
        return None
    values = sorted(r.per_1000_bars for r in rates)
    if values[0] <= 0.0:
        return None
    return values[1] / values[0]


def _expectancy(
    confirmed: Sequence[ConfirmedExtremum],
    bars: list[Bar],
    *,
    costs: CostModel,
    horizon_bars: int,
    risk_per_trade: float,
) -> tuple[EconomicReport | None, int]:
    """Trade the reversal each extremum confirms, after costs."""
    by_time = {bar.close_time_ns: index for index, bar in enumerate(bars)}
    outcomes = []
    for extremum in confirmed:
        index = by_time.get(extremum.known_at_ns)
        if index is None:
            continue
        direction = "short" if extremum.extremum_type == "HIGH" else "long"
        try:
            fill = market_at_next_open(bars, signal_index=index)
            target = fill.price * (0.99 if direction == "short" else 1.01)
            stop = fill.price * (1.01 if direction == "short" else 0.99)
            outcomes.append(
                resolve_outcome(
                    bars,
                    entry_index=index + 1,
                    fill_price=fill.price,
                    target=target,
                    stop=stop,
                    direction=direction,
                    horizon_bars=horizon_bars,
                )
            )
        except (NoFillAvailable, HorizonUnavailable):
            continue

    if not [o for o in outcomes if o.outcome is not Outcome.AMBIGUOUS]:
        return None, 0
    report = economic_report(outcomes, costs=costs, risk_per_trade=risk_per_trade)
    return report, report.trades


def _channel_widths(bars: list[Bar], channel: ChannelModel | None) -> dict[int, float]:
    """The channel width at each bar, for the one mode that needs it.

    Fitted point-in-time, like everything else: the width used at bar `i` comes
    from a fit that saw bars up to `i` and no further.
    """
    if channel is None:
        return {}
    widths: dict[int, float] = {}
    for index, bar in enumerate(bars):
        try:
            widths[index] = channel.fit(bars, as_of_ns=bar.close_time_ns).width_pct
        except ChannelFitError:
            continue
    return widths
