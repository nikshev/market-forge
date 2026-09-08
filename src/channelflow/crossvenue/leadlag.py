"""PRD section 17.2's lead-lag features. Research only.

# @trace: REQ-WP-016

    "Do not convert correlation to trading rule without OOS validation."

That prohibition cannot be checked as written -- the conversion happens in
someone's head and lands as an ordinary-looking condition in a signal. What can
be checked is that the signal path does not import this module, and a test
asserts exactly that (ADR-040).

Every value here carries `research_only = True`, on the value rather than in
documentation, so a reader who found one in a signal would see it there.

OOS validation now exists, in REQ-WP-017's purged folds and REQ-WP-018's
comparison report. Section 17.2's condition is satisfiable rather than
theoretical -- which means someone wanting a lead-lag rule has an ADR to
revisit rather than a rule to route around.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

SECOND_NS = 1_000_000_000
#: Section 17.2's windows.
DEFAULT_WINDOWS_NS: tuple[int, ...] = (SECOND_NS, 5 * SECOND_NS, 10 * SECOND_NS)


@dataclass(frozen=True)
class VenueReturn:
    """One venue's return over one window."""

    venue_id: str
    window_ns: int
    value: float
    observations: int
    research_only: bool = True


@dataclass(frozen=True)
class LaggedCorrelation:
    """How one venue's returns line up with another's, shifted."""

    leader: str
    follower: str
    lag_ns: int
    value: float
    observations: int
    research_only: bool = True


def venue_return(
    prices: list[tuple[int, Decimal]], *, venue_id: str, window_ns: int, at_ns: int
) -> VenueReturn | None:
    """Log return across the window, from prices at or before `at_ns`.

    `None` when the window has no price to open against -- not zero, which
    would read as "the venue did not move".
    """
    visible = sorted((t, p) for t, p in prices if t <= at_ns)
    if not visible:
        return None
    floor = at_ns - window_ns
    opening = [p for t, p in visible if t <= floor]
    if not opening:
        return None
    start, end = opening[-1], visible[-1][1]
    if start <= 0:
        return None
    return VenueReturn(
        venue_id=venue_id,
        window_ns=window_ns,
        value=math.log(float(end / start)),
        observations=len(visible),
    )


def lagged_correlation(
    leader: list[float], follower: list[float], *, leader_id: str, follower_id: str, lag: int
) -> LaggedCorrelation | None:
    """Pearson correlation of the leader against the follower shifted by `lag`.

    `None` on fewer than three aligned pairs or a constant series -- the same
    reasoning as ADR-026's z-score: a correlation of zero means "no linear
    relationship", which is not what "we could not compute one" means.
    """
    if lag < 0:
        raise ValueError("lag must not be negative")
    aligned = list(
        zip(leader[: len(leader) - lag] if lag else leader, follower[lag:], strict=False)
    )
    if len(aligned) < 3:
        return None

    xs = [a for a, _ in aligned]
    ys = [b for _, b in aligned]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denominator = math.sqrt(sum(v * v for v in dx)) * math.sqrt(sum(v * v for v in dy))
    if denominator == 0:
        return None

    return LaggedCorrelation(
        leader=leader_id,
        follower=follower_id,
        lag_ns=lag,
        value=sum(a * b for a, b in zip(dx, dy, strict=True)) / denominator,
        observations=len(aligned),
    )
