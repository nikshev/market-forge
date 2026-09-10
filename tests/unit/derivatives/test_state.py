"""The as-of join over derivatives state (REQ-WP-013)."""

from __future__ import annotations

import pytest

from channelflow.derivatives import AmbiguousState, NoStateAvailable, state_at

from .conftest import BASE_NS, MINUTE_NS, NOT_ABOUT_FRESHNESS, state


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


@pytest.mark.trace("REQ-WP-013")
def test_the_join_never_returns_a_later_state() -> None:
    """SC-006, FR-010, Principle I."""
    states = [state(at=10, oi_usd=1.0), state(at=50, oi_usd=2.0)]

    assert state_at(states, at_ns=at(30), staleness_ns=NOT_ABOUT_FRESHNESS).open_interest_usd == 1.0
    assert state_at(states, at_ns=at(60), staleness_ns=NOT_ABOUT_FRESHNESS).open_interest_usd == 2.0


@pytest.mark.trace("REQ-WP-013")
def test_no_state_at_all_is_a_named_refusal() -> None:
    """A `None` here would be indistinguishable from a state with every field
    empty, which is a thing venues actually send."""
    with pytest.raises(NoStateAvailable):
        state_at([state(at=50)], at_ns=at(10), staleness_ns=NOT_ABOUT_FRESHNESS)


@pytest.mark.trace("REQ-WP-013")
def test_a_later_ingest_time_wins_at_the_same_event_time() -> None:
    """The spec's second edge case. Two states for one instant is a venue
    correcting itself, and the correction is the one to use."""
    states = [
        state(at=10, oi_usd=1.0, ingest_offset=1),
        state(at=10, oi_usd=9.0, ingest_offset=500),
    ]

    assert state_at(states, at_ns=at(30), staleness_ns=NOT_ABOUT_FRESHNESS).open_interest_usd == 9.0


@pytest.mark.trace("REQ-WP-013")
def test_a_tie_on_both_times_is_refused() -> None:
    """Nothing in the data breaks it, and choosing arbitrarily would make the
    answer depend on list order."""
    states = [
        state(at=10, oi_usd=1.0, ingest_offset=7),
        state(at=10, oi_usd=9.0, ingest_offset=7),
    ]

    with pytest.raises(AmbiguousState, match="breaks the tie"):
        state_at(states, at_ns=at(30), staleness_ns=NOT_ABOUT_FRESHNESS)
