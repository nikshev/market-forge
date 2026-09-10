"""PRD section 16.1's funding features.

# @trace: REQ-WP-013
# @trace: REQ-WP-026
# @trace: REQ-BIAS-005

PRD section 41 rule 5: "No using current funding settlement before it becomes
known."

This is the derivatives family's characteristic leak, and it is easy to write
by accident. A `DerivativesState` carries `funding_rate` and
`next_funding_time_ns`; the rate belongs to the interval *ending* at that time.
Before it, the venue may still revise it -- so at any `t` earlier than the
settlement, that rate is an estimate, not a fact, and a feature using it is
using a number the market did not have.

`settled_funding` is the whole guard: it returns rates whose interval closed at
or before `t`, and nothing else in this module reads `funding_rate` directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.derivatives.state import (
    DEFAULT_STALENESS_NS,
    ZScore,
    require_fresh,
    z_score,
)
from channelflow.domain import DerivativesState


@dataclass(frozen=True)
class SettledFunding:
    """A rate whose interval has closed, and when it closed."""

    rate: float
    settled_at_ns: int


def settled_funding(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> list[SettledFunding]:
    """Every rate knowable at `at_ns`, oldest first.

    A state whose `next_funding_time_ns` is after `at_ns` is describing an
    interval still in progress. Its rate is excluded, not because it is
    unknown, but because it is not yet what it will be.

    Refuses when the most recent settlement is older than `staleness_ns`: a
    venue that stopped publishing leaves its last rate in place, and without the
    bound every feature here reports it as the rate now ([[REQ-WP-026]]). The
    *history* behind it is untouched -- `funding_z` reads a long window on
    purpose, and refusing old history would break the feature the rule protects.
    """
    settled: list[SettledFunding] = []
    for state in states:
        if state.funding_rate is None or state.next_funding_time_ns is None:
            continue
        if state.next_funding_time_ns > at_ns:
            continue
        settled.append(
            SettledFunding(rate=state.funding_rate, settled_at_ns=state.next_funding_time_ns)
        )
    ordered = sorted(settled, key=lambda s: s.settled_at_ns)
    if ordered:
        require_fresh(ordered[-1].settled_at_ns, at_ns=at_ns, staleness_ns=staleness_ns)
    return ordered


def current_rate(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> float | None:
    """The most recently settled rate, or nothing."""
    settled = settled_funding(states, at_ns=at_ns, staleness_ns=staleness_ns)
    return settled[-1].rate if settled else None


def funding_z(
    states: list[DerivativesState],
    *,
    at_ns: int,
    window: int = 24,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> ZScore:
    """How unusual the current settled rate is. Refuses per ADR-026."""
    settled = settled_funding(states, at_ns=at_ns, staleness_ns=staleness_ns)
    return z_score([s.rate for s in settled], window=window)


def funding_acceleration(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> float | None:
    """The change in the change: how fast funding is moving, and which way.

    Needs three settled intervals. With two it would be the first difference
    wearing a different name, which is the sort of thing that reads as a
    second signal in a feature list.
    """
    settled = settled_funding(states, at_ns=at_ns, staleness_ns=staleness_ns)
    if len(settled) < 3:
        return None
    third, second, first = settled[-3].rate, settled[-2].rate, settled[-1].rate
    return (first - second) - (second - third)
