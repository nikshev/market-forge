"""The as-of join over derivatives state, and the z-score everything shares.

# @trace: REQ-WP-013
# @trace: REQ-WP-026

The point-in-time rule belongs in one place per package rather than in every
feature function -- the same shape REQ-WP-017's dataset uses, and for the same
reason: a rule each call site has to remember is a rule one call site will
forget.

**That was the intention and it did not happen.** [[REQ-WP-026]] went looking for
callers of `state_at` and found none: funding filters on `next_funding_time_ns`,
open interest builds its own series, and each does its own `<= at_ns`. The
freshness rule below is therefore a free function every reader calls, rather
than a method on a seam nobody uses -- and the next reader has to remember,
which is exactly what this paragraph once claimed nobody would have to.

The z-score lives here too, so funding and open interest cannot drift apart on
what "too few observations" means. It refuses twice (ADR-026): zero is the most
meaningful value a z-score can take, and a feature that says "exactly average"
whenever it has nothing to say reads as a calm market to everything downstream.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from channelflow.domain import DerivativesState

#: How old a reading may be and still be presented as the value now.
#:
#: Stated rather than absent, because absent means infinite and infinite makes
#: PRD §45's Phase 3 acceptance -- "stale REST polling cannot silently reuse old
#: value" -- vacuous. Five minutes is a research default over venues that publish
#: funding and open interest on a minute or better cadence; a caller with a
#: slower venue sets its own (Principle X).
DEFAULT_STALENESS_NS: int = 5 * 60 * 1_000_000_000


class NoStateAvailable(LookupError):
    """No derivatives state at or before the instant asked about."""


class StaleState(LookupError):
    """The newest state is older than the caller will accept as current.

    A separate type from `NoStateAvailable` on purpose: a venue that never
    published and one that stopped publishing are different facts, and a caller
    that wants to retry, alarm or fall back needs to tell them apart.
    """


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


def require_fresh(newest_event_ns: int, *, at_ns: int, staleness_ns: int) -> None:
    """Refuse a reading whose newest observation is too old to be current.

    A free function rather than a method, because the three places that read
    polled state find their newest observation differently -- the latest state,
    the last settled funding interval, the last open-interest point -- and only
    the age is shared.

    It has to be called in each of them. `state_at` was written as the package's
    single point-in-time seam and its docstring says so, but no feature ever
    called it: funding filters on `next_funding_time_ns` and open interest on
    its own series. A staleness rule placed only in `state_at` would have
    protected nothing, which is what [[REQ-WP-026]]'s implementation found.
    """
    if staleness_ns < 0:
        raise ValueError(
            f"staleness_ns is {staleness_ns} and describes no window; a negative "
            "tolerance would accept nothing and say it was about freshness"
        )
    age = at_ns - newest_event_ns
    if age > staleness_ns:
        raise StaleState(
            f"the newest derivatives observation at or before {at_ns} is {age}ns old, "
            f"past the {staleness_ns}ns tolerance; PRD section 45's Phase 3 acceptance "
            "says stale REST polling cannot silently reuse an old value"
        )


def state_at(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> DerivativesState:
    """The latest state at or before `at_ns`, and not too old to be current.

    Never a later one -- point-in-time safety, PRD §45's Phase 3 first
    acceptance criterion -- and never an older one than `staleness_ns`, which is
    its second. A poll that failed, or a venue that stopped publishing, leaves
    the last value in place; without an upper bound on its age it is returned
    exactly as a fresh one and every feature built on it reports a number that
    looks current.

    The check lives here rather than in each feature for the reason this module
    exists at all: a rule each call site has to remember is a rule one call site
    will forget.

    Age is measured from the event time, not the ingest time. A correction that
    arrives late describes an old instant and is old.
    """
    # The negative-tolerance guard lives in `require_fresh`, which owns the rule.
    # A copy here raised the same error with the same words one frame up, and a
    # rule stated twice is owned by neither -- the mutation sweep found it by
    # deleting one and changing nothing.
    eligible = [s for s in states if s.meta.event_time_ns <= at_ns]
    if not eligible:
        raise NoStateAvailable(f"no derivatives state at or before {at_ns}")

    latest_event = max(s.meta.event_time_ns for s in eligible)
    require_fresh(latest_event, at_ns=at_ns, staleness_ns=staleness_ns)
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
