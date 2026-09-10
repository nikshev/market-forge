"""EXP-001: comparing the five channel models.

# @trace: REQ-EXP-001

    Compare: rolling OLS std bands; rolling OLS residual quantiles; Huber + MAD;
    quantile regression; Kalman.

    Metrics: next-H coverage; boundary interaction stability; number of false
    "perfect" historical touches; slope stability; width stability;
    computational cost; rejection strategy expectancy OOS.

EXP-001 names the seven metrics and defines none of them, so the definitions are
here and each is stated in the docstring of the function that computes it. A
reader who disagrees should be able to disagree with a definition rather than
with a number.

Two of them had a real choice behind them, recorded in [[ADR-049]]: what counts
as a "false perfect touch", and why computational cost is an operation count
rather than a stopwatch reading.

The seventh metric waited for [[REQ-BT-001]]. Expectancy after costs needs PRD
section 40's outcomes and section 25.4's fills, and until those existed this
experiment could not be run at all -- which is why its requirement note sat at
`draft` while four other experiments' did.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from statistics import pstdev

from channelflow.backtest import (
    BacktestRunner,
    CostModel,
    CostsRequired,
    HorizonUnavailable,
    NoFillAvailable,
    Outcome,
    economic_report,
    market_at_next_open,
    resolve_outcome,
)
from channelflow.bars import Bar
from channelflow.channels import (
    ChannelFitError,
    ChannelModel,
    ChannelSnapshot,
    HuberChannel,
    KalmanChannel,
    QuantileChannel,
    RollingOLSChannel,
)
from channelflow.experiments import ConfigValue, Field, config_of
from channelflow.signals import CandidateState, SignalMachine

#: PRD §41 rule 11: which experiment this module is, and the comparison its
#: entry point returns. `tests/unit/research/test_gate_adoption.py` discovers
#: these rather than being handed a list.
EXPERIMENT = "EXP-001"

#: EXP-001's five, in the PRD's order. The first two are one fitter under two
#: width options -- PRD section 13.2 lists both and prefers the second.
MODELS: dict[str, ChannelModel] = {
    "rolling_ols_std_bands": RollingOLSChannel(bands="std"),
    "rolling_ols_residual_quantiles": RollingOLSChannel(),
    "huber_mad": HuberChannel(),
    "quantile_regression": QuantileChannel(),
    "kalman": KalmanChannel(),
}

#: How far ahead coverage looks. "Next-H" in EXP-001's own words; a research
#: default, held equal across models because the comparison is between them.
DEFAULT_HORIZON = 10

#: A close within this fraction of the channel's width from a boundary is "at"
#: it. Section 13.11's zone bounds are the engine's answer to the same question;
#: this is the measurement's, and it is held constant across models.
TOUCH_BAND = 0.02

#: The share of the series held out. PRD section 41 rule 10 keeps it untouched.
DEFAULT_TEST_FRACTION = 0.3


class SeriesTooShort(ValueError):
    """Not enough bars for every model's lookback plus a horizon and a split."""


@dataclass(frozen=True)
class ModelEntry:
    """One model's seven metrics, or why it has none."""

    model: str
    fits: int = 0
    coverage: float | None = None
    boundary_stability: float | None = None
    false_perfect_touches: int = 0
    slope_stability: float | None = None
    width_stability: float | None = None
    cost_units: int = 0
    trades: int = 0
    expectancy_r: float | None = None
    expectancy_note: str = ""
    reason: str = ""


@dataclass(frozen=True)
class ChannelComparisonReport:
    """Every model, and the conditions all of them shared."""

    entries: dict[str, ModelEntry]
    in_sample_bars: int
    out_of_sample_bars: int
    horizon: int
    costs: CostModel
    settings: dict[str, str] = field(default_factory=dict)
    #: Each model's own configuration, kept because the caller may have supplied
    #: the models. Reconstructing them from `MODELS` would be right for the
    #: default call and silently wrong for every `models=` one.
    configs: dict[str, Mapping[str, ConfigValue]] = field(default_factory=dict)

    @property
    def compared(self) -> Field:
        """EXP-001 ranks nothing.

        Its seven metrics trade off against each other and the PRD names no
        weighting, so the report is the whole field and the choice is the
        reader's. `chosen` is `None` for that reason and not for lack of a
        winner: inventing one here would manufacture the claim PRD §41 rule 11
        exists to make checkable.
        """
        return Field(variants=self.configs, chosen=None)


#: The comparison EXP-001's entry point returns.
COMPARISON = ChannelComparisonReport


def compare_channel_models(
    bars: list[Bar],
    *,
    costs: CostModel | None,
    models: Mapping[str, ChannelModel] | None = None,
    horizon: int = DEFAULT_HORIZON,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    min_quality: float = 0.5,
    risk_per_trade: float = 0.02,
) -> ChannelComparisonReport:
    """Run every model over one series and report EXP-001's seven metrics."""
    if costs is None:
        # The same refusal REQ-BT-001 makes, raised here so a caller learns it
        # before waiting for five model runs.
        raise CostsRequired(
            "PRD section 41 rule 9 requires fees and slippage in any economic "
            "evaluation, and EXP-001's seventh metric is one"
        )

    chosen = dict(models) if models is not None else dict(MODELS)
    longest = max(model.lookback for model in chosen.values())
    split = int(len(bars) * (1.0 - test_fraction))
    if split <= longest + horizon or len(bars) - split <= horizon:
        raise SeriesTooShort(
            f"{len(bars)} bars cannot hold a {longest}-bar lookback, a {horizon}-bar "
            f"horizon and a {test_fraction:.0%} test split; models fitted on different "
            "amounts of history are not being compared with each other"
        )

    # Shared across every variant, and part of each variant's identity: two runs
    # of one model under different settings are two different runs.
    settings = {
        "touch_band": str(TOUCH_BAND),
        "min_quality": str(min_quality),
        "risk_per_trade": str(risk_per_trade),
        "test_fraction": str(test_fraction),
    }

    entries: dict[str, ModelEntry] = {}
    for name, model in chosen.items():
        try:
            entries[name] = _measure(
                name,
                model,
                bars,
                split=split,
                horizon=horizon,
                costs=costs,
                min_quality=min_quality,
                risk_per_trade=risk_per_trade,
            )
        except ChannelFitError as exc:
            # One model's refusal is a fact about that model. Ending the run
            # would make the comparison unavailable whenever any candidate
            # failed -- which is when it is most wanted.
            entries[name] = ModelEntry(model=name, reason=str(exc))

    return ChannelComparisonReport(
        entries=entries,
        configs={name: {**settings, **config_of(model)} for name, model in chosen.items()},
        in_sample_bars=split,
        out_of_sample_bars=len(bars) - split,
        horizon=horizon,
        costs=costs,
        settings=settings,
    )


def _measure(
    name: str,
    model: ChannelModel,
    bars: list[Bar],
    *,
    split: int,
    horizon: int,
    costs: CostModel,
    min_quality: float,
    risk_per_trade: float,
) -> ModelEntry:
    """The six structural metrics in sample, and expectancy out of sample."""
    snapshots: list[tuple[int, ChannelSnapshot]] = []
    for index in range(model.lookback - 1, split):
        snapshots.append((index, model.fit(bars, as_of_ns=bars[index].close_time_ns)))

    covered = _coverage(bars, snapshots, horizon=horizon)
    slopes = [s.slope_normalized for _, s in snapshots]
    widths = [s.width_pct for _, s in snapshots]

    expectancy, trades, note = _out_of_sample_expectancy(
        model,
        bars,
        split=split,
        horizon=horizon,
        costs=costs,
        min_quality=min_quality,
        risk_per_trade=risk_per_trade,
    )

    return ModelEntry(
        model=name,
        fits=len(snapshots),
        coverage=covered,
        boundary_stability=_boundary_stability(bars, snapshots),
        false_perfect_touches=_false_perfect_touches(bars, snapshots),
        slope_stability=pstdev(slopes) if len(slopes) > 1 else 0.0,
        width_stability=pstdev(widths) if len(widths) > 1 else 0.0,
        cost_units=_cost_units(model, fits=len(snapshots)),
        trades=trades,
        expectancy_r=expectancy,
        expectancy_note=note,
    )


def _coverage(
    bars: list[Bar], snapshots: list[tuple[int, ChannelSnapshot]], *, horizon: int
) -> float | None:
    """The share of the next `horizon` closes that fell inside the channel.

    Forward from each fit, which is what coverage means: the channel is fitted
    on data up to `t` and scored on what followed. That is an evaluation, not a
    feature -- nothing computed here is ever fed back into a fit.

    `None` for a degenerate channel: a zero-width band covers nothing or
    everything depending on rounding, and neither is a measurement.
    """
    inside = total = 0
    for index, snapshot in snapshots:
        if snapshot.upper_now <= snapshot.lower_now:
            continue
        for candle in bars[index + 1 : index + 1 + horizon]:
            close = float(candle.close)
            total += 1
            if snapshot.lower_now <= close <= snapshot.upper_now:
                inside += 1
    return inside / total if total else None


def _at_boundary(close: float, snapshot: ChannelSnapshot) -> bool:
    """Whether a close sits within `TOUCH_BAND` of either boundary."""
    width = snapshot.upper_now - snapshot.lower_now
    if width <= 0:
        return False
    margin = width * TOUCH_BAND
    return abs(close - snapshot.upper_now) <= margin or abs(close - snapshot.lower_now) <= margin


def _boundary_stability(
    bars: list[Bar], snapshots: list[tuple[int, ChannelSnapshot]]
) -> float | None:
    """The share of bars whose boundary classification survives the next refit.

    A channel that calls a bar a touch and then, one bar later, does not, is a
    channel whose zones move under the signal engine reading them.
    """
    agreed = total = 0
    for (index, earlier), (_, later) in zip(snapshots, snapshots[1:], strict=False):
        close = float(bars[index].close)
        total += 1
        if _at_boundary(close, earlier) == _at_boundary(close, later):
            agreed += 1
    return agreed / total if total else None


def _false_perfect_touches(bars: list[Bar], snapshots: list[tuple[int, ChannelSnapshot]]) -> int:
    """Bars the last channel calls a touch and the channel of the time did not.

    EXP-001's "number of false 'perfect' historical touches". A chart drawn with
    the current fit is full of bars that kissed the boundary exactly; this counts
    how many of them were nothing of the sort when they happened. It is PRD
    section 2.1's critical risk, measured.
    """
    if not snapshots:
        return 0
    _, latest = snapshots[-1]
    return sum(
        1
        for index, as_seen_then in snapshots
        if _at_boundary(float(bars[index].close), latest)
        and not _at_boundary(float(bars[index].close), as_seen_then)
    )


def _cost_units(model: ChannelModel, *, fits: int) -> int:
    """A deterministic figure for what a model costs to run ([[ADR-049]]).

    The dominant term of one fit, times the number of fits. A stopwatch reading
    would change between runs, and a report that cannot be compared with itself
    cannot be compared with another.
    """
    n = model.lookback
    per_fit = {
        # Least squares over the window, twice for the reweighting loop's start.
        RollingOLSChannel: n,
        # Iteratively reweighted least squares: one pass per iteration.
        HuberChannel: n * getattr(model, "iterations", 20),
        # Every pair of points, three times -- once per quantile.
        QuantileChannel: 3 * n * (n - 1) // 2,
        # One forward pass, one observation at a time.
        KalmanChannel: n,
    }.get(type(model), n)
    return per_fit * fits


def _out_of_sample_expectancy(
    model: ChannelModel,
    bars: list[Bar],
    *,
    split: int,
    horizon: int,
    costs: CostModel,
    min_quality: float,
    risk_per_trade: float,
) -> tuple[float | None, int, str]:
    """Expectancy in R over the held-out segment, after costs.

    The rejection rule is fixed and the same for every model: enter at the next
    open after a confirmation, stop beyond the boundary that was rejected, take
    profit at the channel's centre. Which rule it is matters less than that it is
    one rule -- EXP-001 compares channel models, not exit policies.

    PRD section 41 rule 10 keeps the test segment untouched: the models are not
    tuned here, so the split is a boundary on measurement rather than on fitting.
    """
    runner = BacktestRunner(channel=model, machine=SignalMachine(min_quality=min_quality))
    report = runner.run(bars)

    confirmations = [
        transition
        for transition in report.transitions
        if transition.to_state is CandidateState.CONFIRMED
        and transition.bar_close_time_ns >= bars[split].close_time_ns
    ]
    if not confirmations:
        return None, 0, "no confirmed setup in the out-of-sample segment"

    by_time = {bar.close_time_ns: index for index, bar in enumerate(bars)}
    outcomes = []
    for transition in confirmations:
        index = by_time.get(transition.bar_close_time_ns)
        if index is None:
            continue
        snapshot = model.fit(bars, as_of_ns=bars[index].close_time_ns)
        close = float(bars[index].close)
        upper = snapshot.upper_now >= close >= snapshot.center_now
        direction = "short" if upper else "long"
        stop = snapshot.upper_now if upper else snapshot.lower_now
        try:
            fill = market_at_next_open(bars, signal_index=index)
            outcomes.append(
                resolve_outcome(
                    bars,
                    entry_index=index + 1,
                    fill_price=fill.price,
                    target=snapshot.center_now,
                    stop=stop,
                    direction=direction,
                    horizon_bars=horizon,
                )
            )
        except (NoFillAvailable, HorizonUnavailable):
            # A setup too close to the end of the series has no measurable
            # outcome. Dropped rather than resolved as a timeout, which would
            # count the end of the data as a result.
            continue

    resolved = [o for o in outcomes if o.outcome is not Outcome.AMBIGUOUS]
    if not resolved:
        return None, 0, f"{len(outcomes)} setup(s), none with a resolvable outcome"

    economics = economic_report(outcomes, costs=costs, risk_per_trade=risk_per_trade)
    return economics.expectancy_r, economics.trades, ""
