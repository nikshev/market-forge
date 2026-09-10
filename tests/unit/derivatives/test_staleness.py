"""A stale derivatives state is refused (REQ-WP-026).

PRD §45's Phase 3 acceptance: "stale REST polling cannot silently reuse old
value". The first criterion beside it -- point-in-time safety -- held from the
start; this one did not, and a funding rate from a day ago was returned exactly
as a fresh one.
"""

from __future__ import annotations

import pytest

from channelflow.derivatives import (
    DEFAULT_STALENESS_NS,
    NoStateAvailable,
    StaleState,
    funding_z,
    state_at,
)
from channelflow.derivatives.funding import current_rate

from .conftest import BASE_NS, MINUTE_NS, state


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


@pytest.mark.trace("REQ-WP-026")
def test_a_state_within_the_tolerance_is_returned() -> None:
    states = [state(at=0, funding=0.0001)]

    found = state_at(states, at_ns=at(4), staleness_ns=5 * MINUTE_NS)

    assert found.funding_rate == 0.0001


@pytest.mark.trace("REQ-WP-026")
def test_a_state_older_than_the_tolerance_is_refused() -> None:
    """The criterion itself. A poll that failed leaves the last value in place,
    and nothing downstream could tell."""
    states = [state(at=0, funding=0.0001)]

    with pytest.raises(StaleState) as raised:
        state_at(states, at_ns=at(60), staleness_ns=5 * MINUTE_NS)

    assert str(60 * MINUTE_NS) in str(raised.value)
    assert str(5 * MINUTE_NS) in str(raised.value)


@pytest.mark.trace("REQ-WP-026")
def test_a_state_exactly_at_the_tolerance_is_fresh() -> None:
    """The boundary is stated rather than left to the implementation, because
    one left there changes when somebody refactors."""
    states = [state(at=0, funding=0.0001)]

    assert state_at(states, at_ns=at(5), staleness_ns=5 * MINUTE_NS)

    with pytest.raises(StaleState):
        state_at(states, at_ns=at(5) + 1, staleness_ns=5 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-026")
def test_a_stale_state_and_no_state_are_different_refusals() -> None:
    """A venue that never published and one that stopped are different facts,
    and a single exception type would merge them."""
    with pytest.raises(NoStateAvailable):
        state_at([], at_ns=at(1), staleness_ns=5 * MINUTE_NS)

    with pytest.raises(StaleState):
        state_at([state(at=0)], at_ns=at(60), staleness_ns=5 * MINUTE_NS)

    assert not issubclass(StaleState, NoStateAvailable)
    assert not issubclass(NoStateAvailable, StaleState)


@pytest.mark.trace("REQ-WP-026")
def test_a_negative_tolerance_is_refused() -> None:
    """It describes no window."""
    with pytest.raises(ValueError, match="staleness"):
        state_at([state(at=0)], at_ns=at(1), staleness_ns=-1)


@pytest.mark.trace("REQ-WP-026")
def test_the_default_tolerance_is_about_polling_not_merely_finite() -> None:
    """Absent means infinite, and infinite makes the criterion vacuous -- but so
    does a default of thirty years, which is finite and useless.

    The bound asserted here is the claim the default makes: this is a tolerance
    for data polled every minute or so, and a reading an hour old is not the
    value now under any reading of Phase 3's acceptance.
    """
    assert 0 < DEFAULT_STALENESS_NS <= 60 * MINUTE_NS

    with pytest.raises(StaleState):
        state_at([state(at=0)], at_ns=at(0) + DEFAULT_STALENESS_NS + 1)


@pytest.mark.trace("REQ-WP-026")
def test_open_interest_refuses_a_stale_reading_too() -> None:
    """Funding and open interest are polled separately and read separately, so
    the rule has to be in both places -- there is no shared path that would
    have covered the second for free."""
    from channelflow.derivatives import oi_change, oi_series

    states = [state(at=0, oi_usd=1_000_000.0)]

    with pytest.raises(StaleState):
        oi_series(states, at_ns=at(60), staleness_ns=5 * MINUTE_NS)

    with pytest.raises(StaleState):
        oi_change(states, at_ns=at(60), window_ns=5 * MINUTE_NS, staleness_ns=5 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-026")
def test_a_feature_inherits_the_refusal_without_re_checking_it() -> None:
    """A rule each call site has to remember is a rule one call site will
    forget -- `state_at`'s own docstring, and the reason the check lives there
    rather than in every feature."""
    states = [state(at=0, funding=0.0001, next_funding_at=0)]

    with pytest.raises(StaleState):
        current_rate(states, at_ns=at(60), staleness_ns=5 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-026")
def test_a_z_score_still_reads_the_history_behind_a_fresh_value() -> None:
    """The rule is about a value read as current, not about the history behind
    it. Applied to the window instead, it would refuse the feature exactly when
    it has the most to say -- and look like the rule working."""
    states = [
        state(at=minute, funding=0.0001 * (minute % 5), next_funding_at=minute)
        for minute in range(120)
    ]

    z = funding_z(states, at_ns=at(119), staleness_ns=5 * MINUTE_NS, window=100)

    assert z.observations > 50


@pytest.mark.trace("REQ-WP-026")
def test_a_feature_with_nothing_settled_reports_nothing_rather_than_stale() -> None:
    """No value is not an old value.

    A venue that has published states but settled no interval has nothing to be
    stale about, and refusing here would report a freshness problem where the
    honest answer is that there is no rate yet.
    """
    states = [state(at=0, funding=0.0001)]

    assert current_rate(states, at_ns=at(60), staleness_ns=5 * MINUTE_NS) is None


@pytest.mark.trace("REQ-WP-026")
def test_which_state_wins_at_one_instant_is_unchanged() -> None:
    """The correction rule is untouched: a later ingest is later information
    about the same instant."""
    states = [
        state(at=0, funding=0.0001, ingest_offset=1),
        state(at=0, funding=0.0009, ingest_offset=99),
    ]

    assert state_at(states, at_ns=at(1)).funding_rate == 0.0009
