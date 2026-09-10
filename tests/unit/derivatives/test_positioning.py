"""Long/short positioning, and its absence (REQ-WP-031)."""

from __future__ import annotations

import pytest

from channelflow.derivatives import (
    NoStateAvailable,
    StaleState,
    ZScoreUnavailable,
    long_short_ratio,
    long_short_z,
    top_trader_z,
)
from channelflow.domain import DerivativesState

from .conftest import BASE_NS, MINUTE_NS, NOT_ABOUT_FRESHNESS, meta


def state(*, at: int, ratio: float | None = None, top: float | None = None) -> DerivativesState:
    return DerivativesState(
        meta=meta(at),
        long_short_ratio=ratio,
        top_trader_long_short_ratio=top,
    )


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


# --- carried, or its absence is ---------------------------------------------


@pytest.mark.trace("REQ-WP-031")
def test_a_venue_that_publishes_nothing_is_not_a_balanced_market() -> None:
    """The failure this whole requirement is about.

    A ratio of 1.0 says longs and shorts are even, which is a reading. An absent
    ratio says nobody knows. Collapsing them puts a confident "balanced" in
    front of every instrument on every venue that does not publish, and nothing
    downstream ever sees a gap.
    """
    silent = state(at=0)
    balanced = state(at=1, ratio=1.0)

    assert silent.long_short_ratio is None
    assert balanced.long_short_ratio == 1.0


@pytest.mark.trace("REQ-WP-031")
def test_the_two_ratios_are_independent() -> None:
    """A global account ratio and a top-trader position ratio measure different
    populations. A venue may publish one and not the other."""
    partial = state(at=0, ratio=1.8)

    assert partial.long_short_ratio == 1.8
    assert partial.top_trader_long_short_ratio is None


@pytest.mark.trace("REQ-WP-031")
@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_a_non_positive_ratio_is_refused(bad: float) -> None:
    """A ratio of zero means no longs at all, which no venue reports and which
    would break every ratio built on it."""
    with pytest.raises(ValueError):
        state(at=0, ratio=bad)


@pytest.mark.trace("REQ-WP-031")
def test_the_latest_published_ratio_is_the_current_one() -> None:
    states = [state(at=0, ratio=1.2), state(at=5, ratio=2.4)]

    assert long_short_ratio(states, at_ns=at(6), staleness_ns=NOT_ABOUT_FRESHNESS) == 2.4


@pytest.mark.trace("REQ-WP-031")
def test_a_ratio_nobody_published_reads_as_nothing() -> None:
    """Not zero, not one."""
    states = [state(at=0), state(at=5)]

    assert long_short_ratio(states, at_ns=at(6), staleness_ns=NOT_ABOUT_FRESHNESS) is None


# --- crowding is relative ----------------------------------------------------


@pytest.mark.trace("REQ-WP-031")
def test_the_same_ratio_is_unusual_on_one_history_and_ordinary_on_another() -> None:
    """The criterion that cannot be satisfied by accident.

    2.0 is extreme for an instrument that has sat near 1.0 and ordinary for one
    that has sat near 2.0 -- which is why a ratio alone is not squeeze context.
    """
    calm = [state(at=i, ratio=1.0 + (i % 2) * 0.02) for i in range(40)]
    calm.append(state(at=40, ratio=2.0))

    crowded = [state(at=i, ratio=2.0 + (i % 2) * 0.02) for i in range(40)]
    crowded.append(state(at=40, ratio=2.0))

    surprising = long_short_z(calm, at_ns=at(41), staleness_ns=NOT_ABOUT_FRESHNESS)
    ordinary = long_short_z(crowded, at_ns=at(41), staleness_ns=NOT_ABOUT_FRESHNESS)

    assert surprising.value > 3.0
    assert abs(ordinary.value) < 1.5


@pytest.mark.trace("REQ-WP-031")
def test_too_little_history_is_refused_rather_than_called_average() -> None:
    """ADR-026: zero is the most meaningful value a z-score can take, and a
    feature that says "exactly average" whenever it has nothing to say reads as
    a calm market to everything downstream."""
    with pytest.raises(ZScoreUnavailable):
        long_short_z([state(at=0, ratio=1.5)], at_ns=at(1), staleness_ns=NOT_ABOUT_FRESHNESS)


@pytest.mark.trace("REQ-WP-031")
def test_the_count_travels_with_the_reading() -> None:
    """A window of three readings and one of three hundred are different
    claims, and nothing in the number itself says which it is.

    The shared z-score refuses a window it cannot fill rather than shortening
    it, so a successful reading is always over exactly its window -- and the
    count says which window was asked for.
    """
    states = [state(at=i, ratio=1.0 + (i % 3) * 0.1) for i in range(30)]

    narrow = long_short_z(states, at_ns=at(30), window=10, staleness_ns=NOT_ABOUT_FRESHNESS)
    wide = long_short_z(states, at_ns=at(30), window=25, staleness_ns=NOT_ABOUT_FRESHNESS)

    assert narrow.observations == 10
    assert wide.observations == 25


@pytest.mark.trace("REQ-WP-031")
def test_states_without_a_ratio_do_not_enter_the_history() -> None:
    """A silent venue must not drag the z-score toward anything.

    Asserted by asking for a window only the silent states could fill: with 20
    published readings and 20 silent states, a window of 40 succeeds if silence
    counts as an observation and is refused if it does not, naming the 20 it
    found. A window of 20 would have passed either way -- which is how a test
    like this quietly stops testing.
    """
    published = [state(at=i, ratio=1.0 + (i % 3) * 0.1) for i in range(20)]
    silent = [state(at=20 + i) for i in range(20)]

    with pytest.raises(ZScoreUnavailable, match="found 20"):
        long_short_z(published + silent, at_ns=at(40), window=40, staleness_ns=NOT_ABOUT_FRESHNESS)


@pytest.mark.trace("REQ-WP-031")
def test_the_top_trader_ratio_has_its_own_reading() -> None:
    """Averaged with the account ratio it would describe neither population."""
    states = [state(at=i, ratio=1.0, top=2.0 + (i % 3) * 0.1) for i in range(30)]

    reading = top_trader_z(states, at_ns=at(30), window=30, staleness_ns=NOT_ABOUT_FRESHNESS)

    assert reading.observations == 30
    assert reading.mean > 1.9


# --- the same rules as its neighbours ----------------------------------------


@pytest.mark.trace("REQ-WP-031")
def test_a_stale_reading_is_refused() -> None:
    """The same REST polling as funding, so REQ-WP-026's rule is the same rule
    rather than a similar one."""
    states = [state(at=0, ratio=1.5)]

    with pytest.raises(StaleState):
        long_short_ratio(states, at_ns=at(60), staleness_ns=5 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-031")
def test_no_state_at_all_is_its_own_refusal() -> None:
    with pytest.raises(NoStateAvailable):
        long_short_ratio([], at_ns=at(1), staleness_ns=NOT_ABOUT_FRESHNESS)


@pytest.mark.trace("REQ-WP-031")
def test_the_new_features_are_registered_with_a_null_policy() -> None:
    from channelflow.features import REGISTRY, exposed_feature_names

    exposed_feature_names()

    for name in ("long_short_ratio", "long_short_z", "top_trader_long_short_ratio"):
        assert name in REGISTRY, name
        assert REGISTRY[name].null_policy.strip()


@pytest.mark.trace("REQ-WP-031")
def test_a_venue_that_stopped_publishing_positioning_is_stale() -> None:
    """Freshness belongs to the reading, not to the state that carried it.

    A venue that keeps sending states and stops sending positioning is stale in
    exactly the way this refuses. Measured against the newest state it would be
    called current, and the z-score would be built on a half-hour-old book while
    the connector looked healthy.
    """
    published = [state(at=i, ratio=1.0 + (i % 3) * 0.1) for i in range(30)]
    still_arriving = [state(at=30 + i) for i in range(5)]

    with pytest.raises(StaleState):
        long_short_z(published + still_arriving, at_ns=at(34), staleness_ns=2 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-031")
def test_the_history_stops_at_the_instant_being_asked_about() -> None:
    """Principle I, asserted where it could actually be broken.

    Twenty readings at or before the instant and twenty after it: a window of 40
    can only be filled by reading the future, so it is refused, naming the 20 it
    was allowed to see. A window of 20 would have passed either way.
    """
    known = [state(at=i, ratio=1.0 + (i % 3) * 0.1) for i in range(20)]
    later = [state(at=20 + i, ratio=5.0) for i in range(20)]

    with pytest.raises(ZScoreUnavailable, match="found 20"):
        long_short_z(known + later, at_ns=at(19), window=40, staleness_ns=NOT_ABOUT_FRESHNESS)
