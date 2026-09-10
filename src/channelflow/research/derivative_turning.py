"""EXP-012: which causal slope estimator sees a turn coming.

# @trace: REQ-EXP-012

    Compare: raw trailing return sign change; causal local polynomial order 2;
    causal local polynomial order 3; Kalman filtered slope; one-sided
    Savitzky-Golay-equivalent implementation if retained.

    Evaluate maximum/minimum forecast precision at horizons 3/6/12/24 bars.

    Centered filters are allowed only as retrospective label references, never
    as live candidates.

That last line is the load-bearing one, and this module is where it can most
easily be broken: a centred filter is the best turning-point detector there is,
because it can see both sides of the turn. It is also useless -- its answer at
bar `t` changes when bar `t+1` arrives.

So the labels here are made by a centred filter and the candidates are refused
if they are centred. `require_causal` is REQ-NRT-D's guard and it runs on every
candidate before the comparison starts; the label transform never goes near it.

Precision at a horizon means: of the bars this method called a turn, what share
were within the horizon of a real one. Not recall -- a method that calls every
bar a turn has perfect recall and no information, and precision is what a reader
of an alert actually experiences.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from channelflow.bars import Bar
from channelflow.experiments import ConfigValue, Field, config_of
from channelflow.extrema import CausalTransform, Transform, require_causal

#: EXP-012's horizons, in bars.
HORIZONS: tuple[int, ...] = (3, 6, 12, 24)

#: How far from a labelled turn a call still counts as that turn. A research
#: default: it decides what "found it" means, and PRD section 13A.27's warning
#: applies to it.
DEFAULT_TOLERANCE_BARS = 2


@dataclass(frozen=True)
class Method:
    """One candidate slope estimator, and its causality declaration."""

    name: str
    transform: Transform
    #: Returns the slope at each bar, seeing only bars at or before it.
    slopes: Callable[[Sequence[float]], list[float]]


@dataclass(frozen=True)
class HorizonPrecision:
    """How often this method's calls were near a real turn, at one horizon."""

    horizon: int
    calls: int
    hits: int

    @property
    def precision(self) -> float | None:
        """`None` when the method called nothing: precision over no calls is not
        zero, and a silent method is not a wrong one."""
        return self.hits / self.calls if self.calls else None


@dataclass(frozen=True)
class MethodResult:
    """One method at every horizon."""

    method: str
    by_horizon: tuple[HorizonPrecision, ...]
    turns_called: int


@dataclass(frozen=True)
class TurningComparison:
    """Every method, the labels they were scored against, and how they were made."""

    results: dict[str, MethodResult]
    labelled_turns: int
    label_method: str
    tolerance_bars: int
    configs: dict[str, Mapping[str, ConfigValue]] = field(default_factory=dict)
    note: str = field(
        default=(
            "the labels come from a centred filter, which sees both sides of a turn "
            "and cannot run live; every candidate is causal and was checked "
            "(PRD section 13A.6)"
        )
    )

    @property
    def compared(self) -> Field:
        """Every causal method measured against the centred labels, and no winner.

        The labeller is not in the field. It is how the labels were made, not a
        candidate for anything -- a centred filter cannot run live, which is the
        whole reason the causal methods are being compared at all.
        """
        return Field(variants=self.configs, chosen=None)


class CenteredCandidateRejected(ValueError):
    """A centred transform was offered as a live candidate."""


@dataclass
class CenteredLabeller:
    """A symmetric smoother, for labels only.

    Declares `centered=True`, which is what makes `require_causal` refuse it if
    anyone ever hands it to the live path. It is the best turning-point finder
    here and it is disqualified by construction -- that is the point of the
    declaration rather than a comment saying so.
    """

    name: str = "centered_smoother"
    centered: bool = True
    window: int = 5

    def apply(self, values: list[float]) -> list[float]:
        if len(values) < self.window:
            return list(values)
        kernel = np.ones(self.window) / self.window
        return list(np.convolve(np.array(values), kernel, mode="same"))


def label_turns(bars: list[Bar], *, labeller: CenteredLabeller | None = None) -> list[int]:
    """The indices where the smoothed series changed direction.

    Retrospective by construction and honest about it: PRD section 13A.6 permits
    exactly this use -- "centered peak-finding may create labels and
    diagnostics, never live signals".
    """
    smoother = labeller or CenteredLabeller()
    smoothed = smoother.apply([float(b.close) for b in bars])
    turns: list[int] = []
    for index in range(1, len(smoothed) - 1):
        before, here, after = smoothed[index - 1], smoothed[index], smoothed[index + 1]
        if (here > before and here >= after) or (here < before and here <= after):
            turns.append(index)
    return turns


def trailing_sign_change(values: Sequence[float]) -> list[float]:
    """The rawest candidate: the sign of the last return."""
    out = [0.0]
    for index in range(1, len(values)):
        out.append(values[index] - values[index - 1])
    return out


def local_polynomial(order: int, window: int = 9) -> Callable[[Sequence[float]], list[float]]:
    """A causal local polynomial fit's slope at the right edge of its window.

    At the *right* edge, which is what makes it causal: the estimate at bar `t`
    is the derivative of a polynomial fitted to the bars up to `t`, evaluated
    where they end. Fitted to a window centred on `t` it would be the same
    arithmetic and a different -- and forbidden -- estimator.
    """

    def slopes(values: Sequence[float]) -> list[float]:
        out: list[float] = []
        for index in range(len(values)):
            start = max(0, index - window + 1)
            span = np.array(values[start : index + 1], dtype=np.float64)
            if len(span) <= order:
                out.append(0.0)
                continue
            x = np.arange(len(span), dtype=np.float64)
            coefficients = np.polyfit(x, span, order)
            derivative = np.polyder(coefficients)
            out.append(float(np.polyval(derivative, x[-1])))
        return out

    return slopes


def kalman_slope(
    process: float = 1e-4, observation: float = 1e-2
) -> Callable[[Sequence[float]], list[float]]:
    """A local linear trend filter's slope state, one observation at a time."""

    def slopes(values: Sequence[float]) -> list[float]:
        level, slope = float(values[0]) if values else 0.0, 0.0
        variance = [[1.0, 0.0], [0.0, 1.0]]
        out = [0.0]
        for value in values[1:]:
            level += slope
            variance = [
                [
                    variance[0][0] + variance[0][1] * 2 + variance[1][1] + process,
                    variance[0][1] + variance[1][1],
                ],
                [variance[1][0] + variance[1][1], variance[1][1] + process],
            ]
            innovation = float(value) - level
            denominator = variance[0][0] + observation
            gain_level = variance[0][0] / denominator
            gain_slope = variance[1][0] / denominator
            level += gain_level * innovation
            slope += gain_slope * innovation
            variance = [
                [variance[0][0] * (1 - gain_level), variance[0][1] * (1 - gain_level)],
                [
                    variance[1][0] - gain_slope * variance[0][0],
                    variance[1][1] - gain_slope * variance[0][1],
                ],
            ]
            out.append(slope)
        return out

    return slopes


#: EXP-012's candidates. The Savitzky-Golay equivalent is absent by design: its
#: one-sided form is the causal local polynomial already here, and its centred
#: form is a label maker, not a candidate.
def default_methods() -> tuple[Method, ...]:
    return (
        Method(
            name="trailing_sign_change",
            transform=CausalTransform(name="trailing_sign_change"),
            slopes=trailing_sign_change,
        ),
        Method(
            name="local_polynomial_2",
            transform=CausalTransform(name="local_polynomial_2"),
            slopes=local_polynomial(order=2),
        ),
        Method(
            name="local_polynomial_3",
            transform=CausalTransform(name="local_polynomial_3"),
            slopes=local_polynomial(order=3),
        ),
        Method(
            name="kalman_slope",
            transform=CausalTransform(name="kalman_slope"),
            slopes=kalman_slope(),
        ),
    )


def compare_turning_methods(
    bars: list[Bar],
    *,
    methods: Sequence[Method] | None = None,
    horizons: Sequence[int] = HORIZONS,
    tolerance_bars: int = DEFAULT_TOLERANCE_BARS,
    labeller: CenteredLabeller | None = None,
) -> TurningComparison:
    """Score every causal candidate against centred labels, at each horizon."""
    candidates = tuple(methods) if methods is not None else default_methods()
    for method in candidates:
        try:
            require_causal(method.transform)
        except Exception as exc:  # noqa: BLE001 -- re-raised with the method named
            raise CenteredCandidateRejected(
                f"{method.name!r} declares centred future dependence and cannot be a "
                f"live candidate: {exc}"
            ) from exc

    turns = label_turns(bars, labeller=labeller)
    closes = [float(b.close) for b in bars]

    results: dict[str, MethodResult] = {}
    for method in candidates:
        slopes = method.slopes(closes)
        called = _calls(slopes)
        results[method.name] = MethodResult(
            method=method.name,
            turns_called=len(called),
            by_horizon=tuple(
                _precision_at(called, turns, horizon=horizon, tolerance=tolerance_bars)
                for horizon in horizons
            ),
        )

    smoother = labeller or CenteredLabeller()
    return TurningComparison(
        results=results,
        labelled_turns=len(turns),
        label_method=smoother.name,
        tolerance_bars=tolerance_bars,
        configs={method.name: config_of(method) for method in candidates},
    )


EXPERIMENT = "EXP-012"

#: The comparison this module's entry point returns.
COMPARISON = TurningComparison


def _calls(slopes: Sequence[float]) -> list[int]:
    """Bars where the estimated slope changed sign -- the method's own call."""
    return [
        index
        for index in range(1, len(slopes))
        if slopes[index - 1] != 0.0
        and slopes[index] != 0.0
        and (slopes[index - 1] > 0) != (slopes[index] > 0)
    ]


def _precision_at(
    calls: Sequence[int], turns: Sequence[int], *, horizon: int, tolerance: int
) -> HorizonPrecision:
    """Of the calls made, how many sat near a real turn within the horizon.

    Precision rather than recall: a method that calls every bar a turn has
    perfect recall and no information, and precision is what a reader of an
    alert actually experiences.
    """
    if not turns:
        return HorizonPrecision(horizon=horizon, calls=len(calls), hits=0)
    hits = sum(
        1
        for call in calls
        if any(0 <= turn - call <= horizon or abs(turn - call) <= tolerance for turn in turns)
    )
    return HorizonPrecision(horizon=horizon, calls=len(calls), hits=hits)
