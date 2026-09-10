"""Who is positioned which way, and whether anybody said.

# @trace: REQ-WP-031

PRD §16 asks for "long/short squeeze context where available", and both halves
of that phrase are this module.

**Where available.** A venue that publishes no positioning is not a balanced
market. A ratio of 1.0 says longs and shorts are even -- a reading. An absent
ratio says nobody knows. Collapsing them would put a confident "balanced" in
front of every instrument on every venue that does not publish, and nothing
downstream would ever see a gap to be suspicious of.

**Squeeze context.** A ratio alone is not context: 2.0 is ordinary on one
instrument and extreme on another. Crowding is measured against the instrument's
own recent positioning, through the z-score funding and open interest already
use -- reused rather than reimplemented, because two versions of "too few
observations" would drift and the drift would be invisible: both would return
numbers.
"""

from __future__ import annotations

from channelflow.derivatives.state import (
    DEFAULT_STALENESS_NS,
    ZScore,
    require_fresh,
    state_at,
    z_score,
)
from channelflow.domain import DerivativesState


def long_short_ratio(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> float | None:
    """The most recent account ratio, or nothing.

    Nothing rather than 1.0: this is the value a caller must be able to tell
    apart from a balanced book.
    """
    return state_at(states, at_ns=at_ns, staleness_ns=staleness_ns).long_short_ratio


def top_trader_ratio(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> float | None:
    """The most recent top-trader ratio, or nothing."""
    return state_at(states, at_ns=at_ns, staleness_ns=staleness_ns).top_trader_long_short_ratio


def long_short_z(
    states: list[DerivativesState],
    *,
    at_ns: int,
    window: int = 20,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> ZScore:
    """How crowded the book is against this instrument's own recent positioning.

    Refuses per [[ADR-026]] rather than returning zero: a feature that says
    "exactly average" whenever it has nothing to say reads as a calm market to
    everything downstream, and crowding is exactly the thing a reader would act
    on.
    """
    return _z(states, at_ns=at_ns, window=window, staleness_ns=staleness_ns, top=False)


def top_trader_z(
    states: list[DerivativesState],
    *,
    at_ns: int,
    window: int = 20,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> ZScore:
    """The same reading over the venue's largest accounts."""
    return _z(states, at_ns=at_ns, window=window, staleness_ns=staleness_ns, top=True)


def _z(
    states: list[DerivativesState],
    *,
    at_ns: int,
    window: int,
    staleness_ns: int,
    top: bool,
) -> ZScore:
    """The history behind a reading, and the freshness of the reading itself.

    A state that published no ratio does not enter the history: a silent venue
    must not drag the score toward anything, and a gap is not an observation.

    Freshness is checked on the newest *published* reading rather than on the
    newest state. A venue that kept sending states and stopped sending
    positioning is stale in exactly the way this refuses, and measuring against
    the state would call it current.
    """
    published = [
        (s.meta.event_time_ns, s.top_trader_long_short_ratio if top else s.long_short_ratio)
        for s in states
        if s.meta.event_time_ns <= at_ns
    ]
    readings = [(when, value) for when, value in published if value is not None]
    if readings:
        require_fresh(readings[-1][0], at_ns=at_ns, staleness_ns=staleness_ns)
    return z_score([value for _, value in readings], window=window)
