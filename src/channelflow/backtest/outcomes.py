"""PRD section 40's signal outcomes.

# @trace: REQ-BT-001

    class SignalOutcome:
        signal_id, horizon_end, first_target_time, first_invalidation_time,
        mfe_pct, mae_pct, return_h,
        outcome: Literal["target", "stop", "timeout", "ambiguous"]

    "If bar data cannot determine whether stop/target happened first inside one
     bar, mark `ambiguous` unless lower-timeframe/tick replay resolves it.

     Never choose the favorable ordering."

That last line is the module. A bar whose range contains both levels is the one
place a backtest can flatter itself while both readings look plausible -- and
only one of them is profitable. Resolving it either way produces a number that
survives every review, because nothing downstream can tell which ordering was
assumed.

A touch includes equality with the level. Requiring a strict breach is choosing
the favourable ordering by one tick, on every trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from channelflow.bars import Bar


class Outcome(StrEnum):
    TARGET = "target"
    STOP = "stop"
    TIMEOUT = "timeout"
    #: Both levels inside one bar's range, and the bars cannot say which came
    #: first. Section 40 allows a lower-timeframe replay to resolve it; until
    #: there is one, this is the answer.
    AMBIGUOUS = "ambiguous"


class HorizonUnavailable(LookupError):
    """The horizon reaches past the bars, so nothing can be said about it."""


@dataclass(frozen=True)
class SignalOutcome:
    """Section 40's record, separate from the signal it describes."""

    horizon_end_ns: int
    first_target_time_ns: int | None
    first_invalidation_time_ns: int | None
    mfe_pct: float
    mae_pct: float
    return_h: float
    outcome: Outcome

    @property
    def resolved(self) -> bool:
        """Whether this outcome can carry an economic figure."""
        return self.outcome is not Outcome.AMBIGUOUS


def resolve_outcome(
    bars: list[Bar],
    *,
    entry_index: int,
    fill_price: float,
    target: float,
    stop: float,
    direction: str,
    horizon_bars: int,
) -> SignalOutcome:
    """What happened between the fill and the end of the horizon.

    Refuses when the horizon extends past the bars. An unfinished horizon is not
    a timeout: the answer may be in bars that do not exist yet, and recording
    absence as evidence teaches every study that the end of a dataset is calm.
    """
    last = entry_index + horizon_bars
    if last >= len(bars):
        raise HorizonUnavailable(
            f"the horizon ends at bar {last} and the series has {len(bars)}; an "
            "unfinished horizon is not a timeout"
        )

    long = direction == "long"
    window = bars[entry_index : last + 1]
    horizon_end_ns = window[-1].close_time_ns

    target_at: int | None = None
    stop_at: int | None = None
    ambiguous = False
    best = worst = fill_price

    for candle in window:
        high, low = float(candle.high), float(candle.low)
        best, worst = max(best, high), min(worst, low)

        hit_target = high >= target if long else low <= target
        hit_stop = low <= stop if long else high >= stop
        if hit_target and hit_stop:
            # Both inside one bar. Section 40: never choose the favorable
            # ordering -- and never the unfavourable one either, which would be
            # a different thumb on the same scale.
            ambiguous = True
            break
        if hit_target:
            target_at = candle.close_time_ns
            break
        if hit_stop:
            stop_at = candle.close_time_ns
            break

    if ambiguous:
        outcome = Outcome.AMBIGUOUS
    elif target_at is not None:
        outcome = Outcome.TARGET
    elif stop_at is not None:
        outcome = Outcome.STOP
    else:
        outcome = Outcome.TIMEOUT

    sign = 1.0 if long else -1.0
    exit_price = _exit_price(outcome, target=target, stop=stop, close=float(window[-1].close))
    return SignalOutcome(
        horizon_end_ns=horizon_end_ns,
        # An ambiguous bar claims neither time -- and the loop is what
        # guarantees it, because the ambiguous branch breaks before either can
        # be set. A `None if ambiguous else ...` here would be a second guard
        # over the same property, and it would hide the loss of the first: with
        # it in place, deleting that `break` changes no test.
        first_target_time_ns=target_at,
        first_invalidation_time_ns=stop_at,
        mfe_pct=sign * ((best if long else worst) - fill_price) / fill_price,
        mae_pct=sign * ((worst if long else best) - fill_price) / fill_price,
        return_h=sign * (exit_price - fill_price) / fill_price,
        outcome=outcome,
    )


def _exit_price(outcome: Outcome, *, target: float, stop: float, close: float) -> float:
    """Where the trade left, by what ended it.

    An ambiguous trade exits at the close, and its return is excluded from every
    economic metric anyway -- the field is filled so the record is complete, not
    so the number is used.
    """
    if outcome is Outcome.TARGET:
        return target
    if outcome is Outcome.STOP:
        return stop
    return close
