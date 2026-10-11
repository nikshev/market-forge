"""Open interest, funding (z) and basis as of a bar's close, from stored derivatives states.

# @trace: REQ-WP-093

The collector stores raw observations; this is where they become features ([[ADR-070]]), and it is
pure: no table, no clock, nothing that reaches a storage backend (`test_isolation` holds `features/`
to that). `pipeline/context_pass.py` reads the tables and calls it. Each feature is evaluated
**as of the close** with the derivatives library's own functions, so the library's refusals --
stale, too few observations, a constant series -- are this module's refusals, and a feature that
cannot be computed is absent from the result. Zero is never returned for absence.

**What was knowable at the close.** A state is used when its event time is at or before the close
*and*, for a polled state, when the collector had received it by then: Binance's open-interest
bucket is dated at its own time and arrives later, and a feature built from a state seen after the
close would be using something the market had not yet shown anyone. A settled funding rate is
public from its settlement, however long afterwards the history was loaded, so it is held to its
event time alone.

**Funding is the settled history, never the polled estimate.** `settled_funding` returns every state
whose settlement has passed, and polled states number one a minute; handed to a 24-observation
window they would be 24 estimates of one interval. Only rows sourced `*-funding-history` -- one per
settlement, the rate that was paid -- enter `funding_z`.

"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass

from channelflow.context import sources
from channelflow.derivatives.funding import funding_z
from channelflow.derivatives.openinterest import basis_bps, oi_series
from channelflow.derivatives.state import (
    NoStateAvailable,
    StaleState,
    ZScoreUnavailable,
    state_at,
)
from channelflow.domain import DerivativesState

CONTEXT_FEATURES: tuple[str, ...] = ("open_interest_usd", "funding_z", "basis_bps")

#: How far back from a close the polled states are scanned for one that was already received. A
#: state arrives minutes after its event time at worst; this is orders of magnitude beyond that, and
#: bounds the scan so a bar is O(1) against a table of weeks of states.
_SCAN_BACK = 200

#: Settled rates handed to `funding_z`: its window with room to spare.
_HISTORY_SLICE = sources.FUNDING_WINDOW + 8

_HISTORY_SUFFIX = "-funding-history"
_OI_SOURCE_SUFFIX = "-rest-oi"

_LIBRARY_REFUSALS = (NoStateAvailable, StaleState, ZScoreUnavailable)


@dataclass(frozen=True)
class StateIndex:
    """One perpetual's states, split into polled and settled-history, each sorted by event time."""

    polled: tuple[DerivativesState, ...]
    polled_times: tuple[int, ...]
    history: tuple[DerivativesState, ...]
    history_times: tuple[int, ...]

    @classmethod
    def of(cls, states: Sequence[DerivativesState]) -> StateIndex:
        ordered = sorted(states, key=lambda s: (s.meta.event_time_ns, s.meta.ingest_time_ns))
        settled = tuple(s for s in ordered if s.meta.source.endswith(_HISTORY_SUFFIX))
        polled = tuple(s for s in ordered if not s.meta.source.endswith(_HISTORY_SUFFIX))
        return cls(
            polled=polled,
            polled_times=tuple(s.meta.event_time_ns for s in polled),
            history=settled,
            history_times=tuple(s.meta.event_time_ns for s in settled),
        )


def _latest_received(index: StateIndex, close_ns: int, *, having: str) -> DerivativesState | None:
    """The latest polled state the collector had received by `close_ns` that carries `having`."""
    hi = bisect_right(index.polled_times, close_ns)
    for state in reversed(index.polled[max(0, hi - _SCAN_BACK) : hi]):
        if state.meta.ingest_time_ns > close_ns:
            continue  # seen after the close: not knowable at it
        if getattr(state, having) is not None:
            return state
    return None


def _open_interest(index: StateIndex, close_ns: int) -> float | None:
    state = _latest_received(index, close_ns, having="open_interest_usd")
    if state is None:
        return None
    bound = (
        sources.OPEN_INTEREST_STALENESS_NS
        if state.meta.source.endswith(_OI_SOURCE_SUFFIX)
        else sources.POLLED_STALENESS_NS
    )
    try:
        return oi_series([state], at_ns=close_ns, staleness_ns=bound)[-1].open_interest_usd
    except _LIBRARY_REFUSALS:
        return None


def _basis(index: StateIndex, close_ns: int) -> float | None:
    hi = bisect_right(index.polled_times, close_ns)
    for state in reversed(index.polled[max(0, hi - _SCAN_BACK) : hi]):
        if state.meta.ingest_time_ns > close_ns:
            continue
        if state.mark_price is None or state.index_price is None:
            continue
        try:
            current = state_at([state], at_ns=close_ns, staleness_ns=sources.POLLED_STALENESS_NS)
        except _LIBRARY_REFUSALS:
            return None
        return basis_bps(perp_price=current.mark_price, spot_price=current.index_price)
    return None


def _funding_z(index: StateIndex, close_ns: int) -> float | None:
    hi = bisect_right(index.history_times, close_ns)
    window = list(index.history[max(0, hi - _HISTORY_SLICE) : hi])
    if not window:
        return None
    try:
        return funding_z(
            window,
            at_ns=close_ns,
            window=sources.FUNDING_WINDOW,
            staleness_ns=sources.FUNDING_STALENESS_NS,
        ).value
    except _LIBRARY_REFUSALS:
        return None


def context_values(
    states: Sequence[DerivativesState], *, close_ns: int, index: StateIndex | None = None
) -> dict[str, float]:
    """The context features of one perpetual as of `close_ns`; a feature that cannot be is absent.

    `index` lets the pass build the split once for a whole series; without it one is built here.
    """
    known = index if index is not None else StateIndex.of(states)
    values: dict[str, float | None] = {
        "open_interest_usd": _open_interest(known, close_ns),
        "funding_z": _funding_z(known, close_ns),
        "basis_bps": _basis(known, close_ns),
    }
    return {name: float(value) for name, value in values.items() if value is not None}
