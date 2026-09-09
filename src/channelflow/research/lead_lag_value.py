"""EXP-010: does cross-venue divergence predict anything worth acting on?

# @trace: REQ-EXP-010

    Measure whether divergence contains predictive value after realistic
    latency/costs.

Three words there are the experiment. **Predictive** means out of sample: a
threshold chosen on the same data it is scored on will always look profitable,
and PRD section 41 rule 10 keeps a locked segment for exactly this. **Latency**
means the divergence is not actionable the instant it appears -- by the time an
order arrives the gap may have closed, and a study that enters at the signal bar
is measuring a trade nobody could place. **Costs** is section 41 rule 9.

PRD section 17.2's prohibition governs the subject: "do not convert correlation
to trading rule without OOS validation". [[ADR-040]] keeps the lead-lag module
off the signal path, and that ban extends here -- this module is the validation,
not a licence.

The experiment may conclude that there is nothing here, and does so by returning
([[ADR-042]]) rather than raising.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

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

#: Thresholds, in basis points of divergence, that the in-sample half chooses
#: between. Declared rather than optimized continuously: a grid a reader can see
#: is a grid they can disagree with.
DEFAULT_THRESHOLDS: tuple[float, ...] = (5.0, 10.0, 20.0, 40.0, 80.0)


class Verdict(StrEnum):
    EDGE = "edge"
    NO_EDGE = "no_edge"


@dataclass(frozen=True)
class DivergenceSignal:
    """One instant at which the venues disagreed, and by how much."""

    index: int
    divergence_bps: float
    #: Which way the follower is expected to move. The caller's reading of the
    #: divergence, not this module's -- REQ-WP-016 computes the basis and says
    #: nothing about direction.
    direction: str


@dataclass(frozen=True)
class LeadLagResult:
    """What the study found, and everything needed to disagree with it."""

    verdict: Verdict
    reason: str
    latency_bars: int
    chosen_threshold_bps: float | None = None
    in_sample: EconomicReport | None = None
    out_of_sample: EconomicReport | None = None
    signals_in_sample: int = 0
    signals_out_of_sample: int = 0


def evaluate_divergence(
    bars: list[Bar],
    signals: Sequence[DivergenceSignal],
    *,
    costs: CostModel | None,
    latency_bars: int,
    horizon_bars: int = 10,
    test_fraction: float = 0.3,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    risk_per_trade: float = 0.02,
) -> LeadLagResult:
    """Choose a threshold in sample, then score it out of sample, after costs.

    `latency_bars` has no default. "Realistic latency" is the experiment's own
    phrase and the number belongs to whoever runs it; zero would be a claim
    about the infrastructure made by this module.
    """
    if costs is None:
        raise CostsRequired(
            "EXP-010 asks about value after costs, and PRD section 41 rule 9 governs "
            "any economic evaluation"
        )
    if latency_bars < 0:
        raise ValueError("latency cannot be negative; a signal is not actionable before it exists")

    split = int(len(bars) * (1.0 - test_fraction))
    early = [s for s in signals if s.index < split]
    late = [s for s in signals if s.index >= split]

    if not early or not late:
        return LeadLagResult(
            verdict=Verdict.NO_EDGE,
            reason=(
                f"{len(early)} signal(s) in sample and {len(late)} out of sample; a "
                "threshold cannot be chosen and scored on separate data"
            ),
            latency_bars=latency_bars,
            signals_in_sample=len(early),
            signals_out_of_sample=len(late),
        )

    best_threshold: float | None = None
    best_report: EconomicReport | None = None
    for threshold in thresholds:
        report = _score(
            bars,
            [s for s in early if abs(s.divergence_bps) >= threshold],
            costs=costs,
            latency_bars=latency_bars,
            horizon_bars=horizon_bars,
            risk_per_trade=risk_per_trade,
        )
        if report is None:
            continue
        if best_report is None or report.expectancy_r > best_report.expectancy_r:
            best_threshold, best_report = threshold, report

    if best_threshold is None or best_report is None:
        return LeadLagResult(
            verdict=Verdict.NO_EDGE,
            reason="no threshold produced a resolvable trade in the training segment",
            latency_bars=latency_bars,
            signals_in_sample=len(early),
            signals_out_of_sample=len(late),
        )

    held_out = _score(
        bars,
        [s for s in late if abs(s.divergence_bps) >= best_threshold],
        costs=costs,
        latency_bars=latency_bars,
        horizon_bars=horizon_bars,
        risk_per_trade=risk_per_trade,
    )
    if held_out is None:
        return LeadLagResult(
            verdict=Verdict.NO_EDGE,
            reason=(
                f"the threshold chosen in sample ({best_threshold} bps) produced no "
                "resolvable trade out of sample"
            ),
            latency_bars=latency_bars,
            chosen_threshold_bps=best_threshold,
            in_sample=best_report,
            signals_in_sample=len(early),
            signals_out_of_sample=len(late),
        )

    positive = held_out.expectancy_r > 0.0
    return LeadLagResult(
        verdict=Verdict.EDGE if positive else Verdict.NO_EDGE,
        reason=(
            f"out of sample, after {latency_bars} bar(s) of latency and costs, "
            f"expectancy was {held_out.expectancy_r:.3f}R over {held_out.trades} trade(s)"
        ),
        latency_bars=latency_bars,
        chosen_threshold_bps=best_threshold,
        in_sample=best_report,
        out_of_sample=held_out,
        signals_in_sample=len(early),
        signals_out_of_sample=len(late),
    )


def _score(
    bars: list[Bar],
    signals: Sequence[DivergenceSignal],
    *,
    costs: CostModel,
    latency_bars: int,
    horizon_bars: int,
    risk_per_trade: float,
) -> EconomicReport | None:
    """Trade every signal after the latency, and report what it was worth.

    The entry is `latency_bars` after the signal, then at the next open. A study
    that entered on the signal's own bar would be measuring a trade nobody could
    place -- by the time an order arrives the divergence may already have closed,
    which is the whole question EXP-010 asks.
    """
    outcomes = []
    for signal in signals:
        entry_signal_index = signal.index + latency_bars
        try:
            fill = market_at_next_open(bars, signal_index=entry_signal_index)
            entry_index = entry_signal_index + 1
            # A fixed target and stop in the fill's own units: EXP-010 asks
            # whether the divergence predicts direction, not what the best exit
            # rule is, so the rule is held constant and symmetric.
            target = fill.price * (1.01 if signal.direction == "long" else 0.99)
            stop = fill.price * (0.99 if signal.direction == "long" else 1.01)
            outcomes.append(
                resolve_outcome(
                    bars,
                    entry_index=entry_index,
                    fill_price=fill.price,
                    target=target,
                    stop=stop,
                    direction=signal.direction,
                    horizon_bars=horizon_bars,
                )
            )
        except (NoFillAvailable, HorizonUnavailable, IndexError):
            continue

    if not [o for o in outcomes if o.outcome is not Outcome.AMBIGUOUS]:
        return None
    return economic_report(outcomes, costs=costs, risk_per_trade=risk_per_trade)
