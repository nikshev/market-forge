"""The as-of join over derivatives state, and the z-score everything shares.

# @trace: REQ-WP-013

The point-in-time rule belongs in one place per package rather than in every
feature function -- the same shape REQ-WP-017's dataset uses, and for the same
reason: a rule each call site has to remember is a rule one call site will
forget.

The z-score lives here too, so funding and open interest cannot drift apart on
what "too few observations" means. It refuses twice (ADR-026): zero is the most
meaningful value a z-score can take, and a feature that says "exactly average"
whenever it has nothing to say reads as a calm market to everything downstream.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from channelflow.domain import DerivativesState


class NoStateAvailable(LookupError):
    """No derivatives state at or before the instant asked about."""


class AmbiguousState(ValueError):
    """Two states the data cannot choose between."""


class ZScoreUnavailable(ValueError):
    """The z-score has no value here, and the reason is named (ADR-026)."""


@dataclass(frozen=True)
class ZScore:
    """A z-score and the sample it came from.

    The count travels with the value because a z-score over four observations
    and one over four hundred are not the same claim, and nothing in the number
    itself says which it is.
    """

    value: float
    mean: float
    stdev: float
    observations: int


def state_at(states: list[DerivativesState], *, at_ns: int) -> DerivativesState:
    """The latest state at or before `at_ns` -- never a later one."""
    eligible = [s for s in states if s.meta.event_time_ns <= at_ns]
    if not eligible:
        raise NoStateAvailable(f"no derivatives state at or before {at_ns}")

    latest_event = max(s.meta.event_time_ns for s in eligible)
    at_latest = [s for s in eligible if s.meta.event_time_ns == latest_event]
    if len(at_latest) == 1:
        return at_latest[0]

    # A later ingest time is later information about the same instant -- a
    # venue correcting itself. Equal on both is a tie nothing in the data
    # breaks, and choosing arbitrarily would make the answer depend on list
    # order.
    latest_ingest = max(s.meta.ingest_time_ns for s in at_latest)
    contenders = [s for s in at_latest if s.meta.ingest_time_ns == latest_ingest]
    if len(contenders) > 1:
        raise AmbiguousState(
            f"{len(contenders)} states at {latest_event} share an ingest time; "
            "nothing in the data breaks the tie"
        )
    return contenders[0]


def z_score(values: list[float], *, window: int) -> ZScore:
    """`(x - mean) / stdev` over the trailing window, or a named refusal.

    ADR-026: no fallback value. A caller wanting to proceed without one handles
    the absence at the call site, where the decision is visible.
    """
    if len(values) < window:
        raise ZScoreUnavailable(
            f"a {window}-observation z-score needs {window} values, found {len(values)}"
        )
    recent = values[-window:]
    mean = sum(recent) / len(recent)
    variance = sum((v - mean) ** 2 for v in recent) / len(recent)
    stdev = math.sqrt(variance)
    if stdev == 0.0:
        raise ZScoreUnavailable(
            "the series is constant over the window, so it has no standard "
            "deviation. Returning 0.0 would read as 'exactly average', which is "
            "the one thing a constant series is not telling us"
        )
    return ZScore(
        value=(recent[-1] - mean) / stdev,
        mean=mean,
        stdev=stdev,
        observations=len(recent),
    )


def ratio(numerator: float, denominator: float) -> float | None:
    """A ratio, or nothing.

    Never infinity and never zero on a zero denominator: both are values a
    consumer would plot, and one of them means "balanced".
    """
    if denominator == 0:
        return None
    return numerator / denominator
