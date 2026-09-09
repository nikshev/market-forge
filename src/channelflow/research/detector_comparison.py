"""EXP-003: comparing the four rejection detectors.

# @trace: REQ-EXP-003

    Compare: wick only; close-back-inside; two-bar confirmation; order-flow
    confirmation.

PRD section 21.3 lists the four and says "implement multiple rejection detectors
as plugins". `RejectionDetector` is that plugin point, and three of the four are
built: the fourth needs order-flow features the protocol does not carry, and is
reported as unavailable rather than approximated. A detector scored on inputs it
never saw is a finding about the wiring wearing the clothes of a finding about
the market.

Each detector runs inside the production `SignalMachine`. PRD section 25.2
forbids a second implementation of strategy logic, and a comparison that
reimplemented the lifecycle would be comparing its own copy.

The four metrics are the four things a detector can be wrong about: too few
confirmations, too slow, too eager -- confirming setups that later invalidate --
or unprofitable. A detector can win on lag and lose on expectancy, and the
report says so rather than collapsing them into one score.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median

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
from channelflow.channels import ChannelModel, RollingOLSChannel
from channelflow.research.channel_comparison import DEFAULT_HORIZON, DEFAULT_TEST_FRACTION
from channelflow.signals import (
    CandidateState,
    CloseBackInside,
    RejectionDetector,
    SignalMachine,
    Transition,
    TwoBarConfirmation,
    WickOnly,
)

#: EXP-003's four, in the PRD's order.
DETECTORS: dict[str, RejectionDetector] = {
    "wick_only": WickOnly(),
    "close_back_inside": CloseBackInside(),
    "two_bar_confirmation": TwoBarConfirmation(),
}

#: The fourth, and why it is not in the mapping above. Named rather than
#: omitted: a report silent about it reads as a comparison of four.
UNAVAILABLE: dict[str, str] = {
    "order_flow_confirmation": (
        "the RejectionDetector protocol carries a bar and a channel, and nothing "
        "from REQ-WP-011's order-flow features; scoring it would measure a "
        "detector that never saw the inputs it is named after"
    ),
}


@dataclass(frozen=True)
class DetectorEntry:
    """One detector's four metrics, or why it has none."""

    detector: str
    confirmations: int = 0
    median_lag_bars: float | None = None
    later_invalidated: float | None = None
    trades: int = 0
    expectancy_r: float | None = None
    reason: str = ""


@dataclass(frozen=True)
class DetectorComparisonReport:
    """Every detector, and the conditions all of them shared."""

    entries: dict[str, DetectorEntry]
    ranking: tuple[str, ...]
    in_sample_bars: int
    out_of_sample_bars: int
    costs: CostModel
    note: str = (
        "a detector may win on lag and lose on expectancy; the ranking is by "
        "expectancy after costs and the other three metrics are reported beside it"
    )


def compare_detectors(
    bars: list[Bar],
    *,
    costs: CostModel | None,
    detectors: Mapping[str, RejectionDetector] | None = None,
    unavailable: Mapping[str, str] | None = None,
    channel: ChannelModel | None = None,
    horizon: int = DEFAULT_HORIZON,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    risk_per_trade: float = 0.02,
) -> DetectorComparisonReport:
    """Run each detector through the production machine over one series."""
    if costs is None:
        raise CostsRequired(
            "expectancy is one of the four metrics, and PRD section 41 rule 9 governs "
            "it wherever it is computed"
        )

    chosen = dict(DETECTORS) if detectors is None else dict(detectors)
    missing = dict(UNAVAILABLE) if unavailable is None else dict(unavailable)
    model = channel or RollingOLSChannel()
    split = int(len(bars) * (1.0 - test_fraction))

    entries = {
        name: _measure(
            name,
            detector,
            bars,
            model=model,
            split=split,
            horizon=horizon,
            costs=costs,
            risk_per_trade=risk_per_trade,
        )
        for name, detector in chosen.items()
    }
    for name, reason in missing.items():
        entries[name] = DetectorEntry(detector=name, reason=reason)

    scored = [e for e in entries.values() if e.expectancy_r is not None]
    ranking = tuple(
        e.detector
        # Highest expectancy first, then by name so one run gives one order.
        for e in sorted(scored, key=lambda e: (-(e.expectancy_r or 0.0), e.detector))
    )
    return DetectorComparisonReport(
        entries=entries,
        ranking=ranking,
        in_sample_bars=split,
        out_of_sample_bars=len(bars) - split,
        costs=costs,
    )


def _measure(
    name: str,
    detector: RejectionDetector,
    bars: list[Bar],
    *,
    model: ChannelModel,
    split: int,
    horizon: int,
    costs: CostModel,
    risk_per_trade: float,
) -> DetectorEntry:
    """One run through the production machine, then the metrics over it."""
    runner = BacktestRunner(channel=model, machine=SignalMachine(detector=detector))
    report = runner.run(bars)
    return detector_metrics(
        name,
        candidate_lives(report.transitions),
        bars,
        model=model,
        split=split,
        horizon=horizon,
        costs=costs,
        risk_per_trade=risk_per_trade,
    )


def detector_metrics(
    name: str,
    lives: Sequence[CandidateLife],
    bars: list[Bar],
    *,
    model: ChannelModel,
    split: int,
    horizon: int,
    costs: CostModel,
    risk_per_trade: float,
) -> DetectorEntry:
    """The four metrics over one detector's candidates.

    Separate from the run that produced them, because one of the four is
    unreachable otherwise: a confirmation the market later takes back is a
    specific path through the lifecycle, and no bar series found so far drives
    the machine down it. Handing this function the lives that describe one is how
    that metric gets tested rather than assumed.
    """
    confirmed = [life for life in lives if life.confirmed_at_ns is not None]
    if not confirmed:
        return DetectorEntry(detector=name, reason="no candidate reached confirmation")

    timeframe_ns = bars[0].timeframe_ns
    lags = [
        (life.confirmed_at_ns - life.opened_at_ns) / timeframe_ns  # type: ignore[operator]
        for life in confirmed
    ]
    expectancy, trades = _expectancy(
        confirmed,
        bars,
        model=model,
        split=split,
        horizon=horizon,
        costs=costs,
        risk_per_trade=risk_per_trade,
    )
    return DetectorEntry(
        detector=name,
        confirmations=len(confirmed),
        median_lag_bars=median(lags),
        # The "too eager" measure: confirmations the market took back. A
        # detector can score well on the other three and badly here, which is
        # the failure the metric exists for.
        later_invalidated=sum(1 for life in confirmed if life.invalidated_after_confirm)
        / len(confirmed),
        trades=trades,
        expectancy_r=expectancy,
    )


@dataclass
class CandidateLife:
    """One candidate's path, reconstructed from the flat transition list."""

    opened_at_ns: int
    confirmed_at_ns: int | None = None
    invalidated_after_confirm: bool = False


def candidate_lives(transitions: Sequence[Transition]) -> list[CandidateLife]:
    """Split the run's transitions into one entry per candidate.

    Public because two of the four metrics are computed from what it returns,
    and forcing a confirmation the market later takes back through the whole
    pipeline is far harder than handing this function the transitions that
    describe one.

    The report carries transitions in order and a candidate begins at every
    `NONE -> APPROACH`, which is what makes them separable without an id.
    """
    lives: list[CandidateLife] = []
    for transition in transitions:
        if transition.from_state is CandidateState.NONE:
            lives.append(CandidateLife(opened_at_ns=transition.bar_close_time_ns))
            continue
        if not lives:
            continue
        life = lives[-1]
        if transition.to_state is CandidateState.CONFIRMED:
            life.confirmed_at_ns = transition.bar_close_time_ns
        elif transition.to_state is CandidateState.INVALIDATED and life.confirmed_at_ns is not None:
            # The "too eager" measure: a confirmation the market took back.
            life.invalidated_after_confirm = True
    return lives


def _expectancy(
    lives: Sequence[CandidateLife],
    bars: list[Bar],
    *,
    model: ChannelModel,
    split: int,
    horizon: int,
    costs: CostModel,
    risk_per_trade: float,
) -> tuple[float | None, int]:
    """Expectancy in R over the held-out segment, after costs."""
    by_time = {bar.close_time_ns: index for index, bar in enumerate(bars)}
    outcomes = []
    for life in lives:
        at_ns = life.confirmed_at_ns
        if at_ns is None or at_ns < bars[split].close_time_ns:
            continue
        index = by_time.get(at_ns)
        if index is None:
            continue
        snapshot = model.fit(bars, as_of_ns=at_ns)
        close = float(bars[index].close)
        upper = snapshot.upper_now >= close >= snapshot.center_now
        try:
            fill = market_at_next_open(bars, signal_index=index)
            outcomes.append(
                resolve_outcome(
                    bars,
                    entry_index=index + 1,
                    fill_price=fill.price,
                    target=snapshot.center_now,
                    stop=snapshot.upper_now if upper else snapshot.lower_now,
                    direction="short" if upper else "long",
                    horizon_bars=horizon,
                )
            )
        except (NoFillAvailable, HorizonUnavailable):
            continue

    if not [o for o in outcomes if o.outcome is not Outcome.AMBIGUOUS]:
        return None, 0
    economics = economic_report(outcomes, costs=costs, risk_per_trade=risk_per_trade)
    return economics.expectancy_r, economics.trades
