"""EXP-014: order-flow exhaustion around extrema, explained and then predicted.

# @trace: REQ-EXP-014

    Conditional study around future-labeled meaningful extrema: OFI sign and
    slope; CVD divergence; microprice deviation; spread widening; wall
    replenishment/cancellation; absorption.

    Then repeat point-in-time as a predictive experiment to avoid confusing
    contemporaneous explanation with forecast value.

Two studies, and the second sentence is the whole requirement. A conditional
study around future-labelled extrema is retrospective by construction: it reads
a window that straddles the turn, and it is allowed to, because explaining what
happens at a turn is a real question. What it cannot do is answer the other one.

A signal can sit at an extreme value in the bars *around* every top and still be
worthless at the moment a decision is made -- because the half of the window
that carried the information had not happened yet, or because the same extreme
value occurs just as often on bars where nothing follows. Those two failures
look identical in a conditional study and opposite in a predictive one.

So the two arms here are separate computations over separate windows, and every
signal is reported with both readings side by side. The contemporaneous arm
declares itself retrospective; the predictive arm reads nothing at or after the
bar it is deciding on -- including its own calling threshold, which is taken
from the signal's trailing distribution rather than the whole series. A quantile
over the whole series is a look-ahead that nothing about the number announces.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean, pstdev

import numpy as np

#: PRD EXP-014's six bullets, and the series each one needs. "OFI sign and
#: slope" is one bullet measured as two columns: the direction of the flow and
#: how fast it is changing are different claims, and a study that averaged them
#: would report neither.
BULLETS: dict[str, tuple[str, ...]] = {
    "ofi": ("ofi_sign", "ofi_slope"),
    "cvd_divergence": ("cvd_divergence",),
    "microprice_deviation": ("microprice_deviation",),
    "spread_widening": ("spread_widening",),
    "wall_replenishment_cancellation": ("wall_replenishment",),
    "absorption": ("absorption",),
}

#: Every column the study needs, in the PRD's order.
SIGNALS: tuple[str, ...] = tuple(name for names in BULLETS.values() for name in names)

#: How each signal reads once both arms have run.
EXPLAINS_AND_PREDICTS = "explains and predicts"
EXPLAINS_ONLY = "explains the turn but does not forecast it"
PREDICTS_ONLY = "forecasts the turn without standing out at it"
NEITHER = "neither"


class SeriesMissing(KeyError):
    """A signal EXP-014 names was not supplied."""


class NotEnoughHistory(ValueError):
    """The predictive arm has no bar it can decide on without looking ahead."""


#: Bars before the predictive arm has a distribution to take a threshold from.
#: One prior bar is not a distribution: the quantile of a single value is that
#: value, so every bar would be its own threshold and every bar a call.
WARMUP_BARS = 2


def trailing_calls(
    values: Sequence[float], *, call_quantile: float, warmup: int = WARMUP_BARS
) -> list[int]:
    """Bars whose value exceeds the quantile of the bars strictly before them.

    Public because it carries the property the predictive arm rests on, and a
    property that cannot be tested directly is one nothing enforces: the calls
    made over a prefix are exactly the calls the whole series makes at those
    same bars. A threshold taken from the whole series breaks that equality and
    nothing about the resulting precision would look wrong.

    Strictly above, not at or above. Many order-flow signals sit at one value
    most of the time -- absorption is zero on a quiet bar -- and the quantile of
    such a series *is* that value. Reading it as "at or above" then calls every
    single bar, which produces a precision exactly equal to the base rate and a
    lift of exactly one: indistinguishable from "this signal carries nothing",
    for a reason that has nothing to do with the signal.
    """
    called: list[int] = []
    for index in range(warmup, len(values)):
        threshold = float(np.quantile(np.array(values[:index]), call_quantile))
        if values[index] > threshold:
            called.append(index)
    return called


@dataclass(frozen=True)
class ReadingRule:
    """What counts as explaining, and what counts as forecasting.

    `effect_floor` and `lift_floor` are judgements about the market rather than
    facts about the data, so neither has a default -- PRD section 13A.27's
    warning about research defaults. `minimum_calls` is a sample-size floor and
    carries this module's own, stated here rather than buried in the comparison.

    `lift_floor` has to sit above one, and the reason is worth stating: a lift
    of "anything above 1.0" is not a finding. A signal unrelated to the turns
    lands a few points either side of one by arithmetic accident -- two of the
    control fixtures written for this module read 1.07 and 1.16 over forty
    calls, on waves whose period no turn follows. A rule of `lift > 1.0` calls
    both of those forecasts.
    """

    effect_floor: float
    lift_floor: float
    minimum_calls: int = 10

    def __post_init__(self) -> None:
        if self.effect_floor <= 0.0:
            raise ValueError(
                "effect_floor must be positive; a floor of zero calls every "
                "difference an explanation, including the ones that are noise"
            )
        if self.lift_floor <= 1.0:
            raise ValueError(
                "lift_floor must be above one; a lift of one is a call that carried "
                "no information, and a floor at or below it accepts noise as a forecast"
            )


@dataclass(frozen=True)
class Contemporaneous:
    """What the signal did in the bars around a labelled extremum.

    Retrospective by construction and saying so: the window straddles the turn,
    and the turn was labelled from data that had not arrived when the window
    opened.
    """

    #: Always true. A field rather than a docstring, because the thing a reader
    #: has to carry away from this number is that it is not a forecast.
    retrospective: bool = True
    around_extrema: int = 0
    control_bars: int = 0
    mean_around: float | None = None
    mean_control: float | None = None
    #: Standardised difference, signed. `None` when either side is empty or the
    #: pooled spread is zero -- a difference divided by no spread is not large.
    effect_size: float | None = None


@dataclass(frozen=True)
class Predictive:
    """What the signal was worth at the moment of the decision.

    Nothing here reads a bar at or after the one being decided on, the calling
    threshold included.
    """

    decided_bars: int
    warmup_bars: int
    calls: int
    hits: int
    #: Share of all decidable bars followed by an extremum inside the horizon.
    base_rate: float | None
    #: Share of the *called* bars that were. `None` over no calls: precision
    #: over nothing is not zero.
    precision: float | None
    #: Precision over base rate. One means the call carried no information.
    lift: float | None


@dataclass(frozen=True)
class SignalStudy:
    """One signal, read both ways, and what the pair of readings means."""

    signal: str
    bullet: str
    contemporaneous: Contemporaneous
    predictive: Predictive
    reading: str


@dataclass(frozen=True)
class ExhaustionStudy:
    """EXP-014's two studies, kept apart."""

    signals: dict[str, SignalStudy]
    labelled_extrema: int
    window_bars: int
    horizon_bars: int
    control_gap_bars: int
    call_quantile: float
    rule: ReadingRule
    note: str = field(
        default=(
            "the conditional arm is retrospective: its window straddles a turn labelled "
            "from bars that had not arrived when the window opened. Only the predictive "
            "arm is a forecast, and the two are computed separately so a strong number "
            "in the first cannot be read as evidence for the second (PRD EXP-014)"
        )
    )

    @property
    def explains_but_does_not_predict(self) -> tuple[str, ...]:
        """The signals EXP-014's second sentence exists to catch."""
        return tuple(name for name, study in self.signals.items() if study.reading == EXPLAINS_ONLY)


def study_exhaustion(
    series: Mapping[str, Sequence[float]],
    extrema: Sequence[int],
    *,
    window_bars: int,
    horizon_bars: int,
    control_gap_bars: int,
    call_quantile: float,
    rule: ReadingRule,
) -> ExhaustionStudy:
    """Run both arms over every signal EXP-014 names.

    None of the five numbers below has a default. Each decides what the study
    concludes -- how wide the window around a turn is, how far ahead a forecast
    counts, how far a control bar has to sit from a turn, how extreme a value
    has to be to count as a call, and how large a difference has to be to count
    as an explanation.
    """
    if window_bars < 1 or horizon_bars < 1 or control_gap_bars < 0:
        raise ValueError(
            "window_bars and horizon_bars must be at least one bar and "
            "control_gap_bars cannot be negative"
        )
    if not 0.0 < call_quantile < 1.0:
        raise ValueError(
            f"call_quantile {call_quantile} is outside (0, 1); a quantile of zero calls "
            "every bar and one calls none"
        )

    missing = [name for name in SIGNALS if name not in series]
    if missing:
        raise SeriesMissing(
            f"EXP-014 names {', '.join(missing)}, which were not supplied; a missing "
            "series read as zeros would report 'this signal does nothing' about a "
            "signal nobody measured"
        )

    lengths = {len(series[name]) for name in SIGNALS}
    if len(lengths) != 1:
        raise ValueError(f"the signals have different lengths: {sorted(lengths)}")
    bars = lengths.pop()
    turns = sorted(set(extrema))
    if any(index < 0 or index >= bars for index in turns):
        raise ValueError("an extremum index falls outside the series")

    built: dict[str, SignalStudy] = {}
    for bullet, names in BULLETS.items():
        for name in names:
            values = [float(v) for v in series[name]]
            around = _conditional(
                values,
                turns,
                window_bars=window_bars,
                control_gap_bars=control_gap_bars,
            )
            ahead = _predictive(
                values,
                turns,
                horizon_bars=horizon_bars,
                call_quantile=call_quantile,
            )
            built[name] = SignalStudy(
                signal=name,
                bullet=bullet,
                contemporaneous=around,
                predictive=ahead,
                reading=_read(around, ahead, rule),
            )

    return ExhaustionStudy(
        signals=built,
        labelled_extrema=len(turns),
        window_bars=window_bars,
        horizon_bars=horizon_bars,
        control_gap_bars=control_gap_bars,
        call_quantile=call_quantile,
        rule=rule,
    )


def _conditional(
    values: Sequence[float],
    turns: Sequence[int],
    *,
    window_bars: int,
    control_gap_bars: int,
) -> Contemporaneous:
    """The signal around the turns against the signal far from any turn.

    The window straddles each turn -- `[i - w, i + w]` -- which is exactly what
    makes this arm retrospective and exactly what makes it able to answer its
    own question. A one-sided window here would be the predictive arm with a
    retrospective label, which is the confusion EXP-014 warns about wearing the
    other arm's clothes.
    """
    near: set[int] = set()
    excluded: set[int] = set()
    for turn in turns:
        near.update(range(max(0, turn - window_bars), min(len(values), turn + window_bars + 1)))
        excluded.update(
            range(max(0, turn - control_gap_bars), min(len(values), turn + control_gap_bars + 1))
        )

    around = [values[i] for i in sorted(near)]
    control = [values[i] for i in range(len(values)) if i not in excluded]

    if not around or not control:
        return Contemporaneous(around_extrema=len(around), control_bars=len(control))

    mean_around, mean_control = fmean(around), fmean(control)
    spread = pstdev(around + control)
    return Contemporaneous(
        around_extrema=len(around),
        control_bars=len(control),
        mean_around=mean_around,
        mean_control=mean_control,
        effect_size=((mean_around - mean_control) / spread if spread > 0.0 else None),
    )


def _predictive(
    values: Sequence[float],
    turns: Sequence[int],
    *,
    horizon_bars: int,
    call_quantile: float,
) -> Predictive:
    """The signal at bar `t` against a turn in `(t, t + horizon]`.

    Two things here are look-aheads waiting to happen and neither announces
    itself in the output. The window is trailing, `[0, t)`, because a window
    that reaches forward is the conditional arm again. And the threshold that
    decides whether bar `t` is a call comes from the signal's distribution
    *before* `t`: a quantile taken over the whole series has read every bar the
    forecast is about, and the resulting precision looks like skill.
    """
    turn_set = set(turns)
    # A bar can only be decided once its horizon fits inside the series --
    # otherwise "no turn followed" is a fact about where the data stops.
    last = len(values) - horizon_bars - 1
    if last < WARMUP_BARS:
        raise NotEnoughHistory(
            f"{len(values)} bars with a {horizon_bars}-bar horizon leave no bar with "
            "both a trailing distribution and a full horizon ahead of it"
        )

    def followed_by_a_turn(index: int) -> bool:
        return any(index < turn <= index + horizon_bars for turn in turn_set)

    decidable = range(WARMUP_BARS, last + 1)
    called = [
        index for index in trailing_calls(values, call_quantile=call_quantile) if index <= last
    ]

    decided = len(decidable)
    followed = sum(1 for index in decidable if followed_by_a_turn(index))
    calls = len(called)
    hits = sum(1 for index in called if followed_by_a_turn(index))

    base_rate = followed / decided if decided else None
    precision = hits / calls if calls else None
    return Predictive(
        decided_bars=decided,
        warmup_bars=WARMUP_BARS,
        calls=calls,
        hits=hits,
        base_rate=base_rate,
        precision=precision,
        lift=(
            precision / base_rate
            if precision is not None and base_rate is not None and base_rate > 0.0
            else None
        ),
    )


def _read(around: Contemporaneous, ahead: Predictive, rule: ReadingRule) -> str:
    """The pair of readings, named.

    `EXPLAINS_ONLY` is the finding EXP-014's second sentence exists to produce:
    a signal that sits at an extreme value around every turn and carries nothing
    at the moment anyone could act on it.
    """
    explains = around.effect_size is not None and abs(around.effect_size) >= rule.effect_floor
    predicts = (
        ahead.lift is not None
        and ahead.lift >= rule.lift_floor
        and ahead.calls >= rule.minimum_calls
    )
    if explains and predicts:
        return EXPLAINS_AND_PREDICTS
    if explains:
        return EXPLAINS_ONLY
    if predicts:
        return PREDICTS_ONLY
    return NEITHER
