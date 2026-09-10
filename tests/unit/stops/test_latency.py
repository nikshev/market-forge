"""A stop update is not effective until it is acknowledged (REQ-WP-033).

PRD §44A.27 supplies its own failing example, and it is the first test here.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.stops import (
    ActivationLatency,
    AnchorKind,
    NaiveFixedPercent,
    PricePoint,
    Replay,
    StopAnchor,
    StopPolicy,
)

from .conftest import BASE_NS, at, free, long_position

MS_NS = 1_000_000


def ms(offset: int) -> int:
    """An instant `offset` milliseconds after the position opened."""
    return BASE_NS + offset * MS_NS


def anchor(price: str, known_at: int) -> StopAnchor:
    return StopAnchor(
        kind=AnchorKind.CONFIRMED_SWING,
        price=Decimal(price),
        known_at_ns=known_at,
        description="a confirmed higher low",
    )


def point(when: int, price: str, *, anchors: tuple[StopAnchor, ...] = ()) -> PricePoint:
    return PricePoint(
        at_ns=when,
        price=Decimal(price),
        noise_distance=Decimal("0.1"),
        anchors=anchors,
    )


# --- the PRD's own example ---------------------------------------------------


@pytest.mark.trace("REQ-WP-033")
def test_the_prd_s_own_example() -> None:
    """§44A.27, replayed literally.

        signal computed at 10:15:00.100
        stop modification ack at 10:15:00.260
        market touch at 10:15:00.180

        The new stop was not yet active.

    Entry 100, initial stop 95. At .100 a confirmed low at 99 lets the policy
    tighten. The market touches 98.50 at .180 -- below the stop decided at .100,
    above the stop that was actually active. Under instantaneous activation the
    position exits at 99 on a level the exchange had not yet obeyed.
    """
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(180), "98.50"),
        point(ms(300), "101.00"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.exited is False


@pytest.mark.trace("REQ-WP-033")
def test_a_touch_after_the_acknowledgement_does_exit_on_it() -> None:
    """The other half. A latency that never lets an update land would be a
    different bug wearing this one's clothes."""
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(400), "98.50"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.exited is True
    # 98.85, not 99: section 44A.8's noise buffer sits the stop back from the
    # anchor by 1.5x the noise distance. What matters here is that the exit is
    # on the decided level at all, which before .260 it could not have been.
    assert outcome.requested_stop_price == Decimal("98.85")


# --- the tie, resolved by rule rather than by outcome ------------------------


@pytest.mark.trace("REQ-WP-033")
def test_the_tie_at_the_acknowledgement_instant_does_not_credit_the_new_stop() -> None:
    """A touch at exactly `t + latency` cannot be ordered against the ack.

    §44A.27 forbids resolving that by outcome, so the rule is fixed in advance:
    the old stop applies. Here that rule costs nothing -- the position survives.
    """
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(260), "98.50"),
        point(ms(400), "101.00"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.exited is False


@pytest.mark.trace("REQ-WP-033")
def test_the_same_tie_rule_applies_where_it_costs_something() -> None:
    """SC-004, and the reason the pair exists.

    Here not crediting the new stop is the expensive reading: the position rides
    past the tie and is stopped out lower, at the initial stop, for a worse R
    than the 99 it had asked for. An implementation choosing the ordering by
    which outcome pays better resolves this one the other way; a rule cannot.
    """
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(260), "94.00"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.exited is True
    # The initial stop, not the 99 that was decided but not yet acknowledged.
    assert outcome.requested_stop_price == Decimal("95")


# --- the latency is declared -------------------------------------------------


@pytest.mark.trace("REQ-WP-033")
def test_the_default_is_not_instantaneous() -> None:
    """A default of zero hands the optimistic case to everyone who did not think
    about it, and the optimism arrives looking like a result."""
    assert ActivationLatency().total_ns > 0


@pytest.mark.trace("REQ-WP-033")
def test_the_default_total_is_the_prd_s_own_gap() -> None:
    """160ms: signal computed at .100, acknowledged at .260. The only figure the
    PRD gives, on the only leg its example measures."""
    assert ActivationLatency().total_ns == 160 * MS_NS
    assert ActivationLatency().decision_ns == 0
    assert ActivationLatency().computation_ns == 0


@pytest.mark.trace("REQ-WP-033")
def test_the_legs_add_up() -> None:
    latency = ActivationLatency(decision_ns=1, computation_ns=2, exchange_ns=3)

    assert latency.total_ns == 6


@pytest.mark.trace("REQ-WP-033")
def test_a_stop_obeyed_before_it_was_decided_is_refused() -> None:
    """Not a slow exchange -- a broken model."""
    with pytest.raises(ValueError):
        ActivationLatency(exchange_ns=-1)


@pytest.mark.trace("REQ-WP-033")
def test_the_instantaneous_case_is_expressible() -> None:
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(180), "98.50"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency.none()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.exited is True
    assert outcome.requested_stop_price == Decimal("98.85")


@pytest.mark.trace("REQ-WP-033")
def test_a_report_names_the_latency_it_ran_under() -> None:
    """Two reports produced under different latencies are not comparable, and
    nothing about their shape says so."""
    path = [point(at(1), "101.00"), point(at(2), "102.00")]
    replay = Replay(costs=free(), latency=ActivationLatency(exchange_ns=7))
    outcome = replay.run_adaptive(long_position(), path, StopPolicy(cooldown_ns=0))

    report = replay.report((outcome,))

    assert report.latency.total_ns == 7


@pytest.mark.trace("REQ-WP-033")
def test_the_naive_baselines_wait_too() -> None:
    """A baseline obeyed instantly while the adaptive policy waits is not a
    comparison of policies: part of the difference would be the latency."""
    path = [point(ms(100), "110.00"), point(ms(180), "104.00")]

    waiting = Replay(costs=free(), latency=ActivationLatency()).run_naive(
        long_position(), path, NaiveFixedPercent()
    )
    instant = Replay(costs=free(), latency=ActivationLatency.none()).run_naive(
        long_position(), path, NaiveFixedPercent()
    )

    assert instant.exited is True
    assert waiting.exited is False


# --- decided is not obeyed ---------------------------------------------------


@pytest.mark.trace("REQ-WP-033")
def test_a_latency_longer_than_the_path_leaves_the_initial_stop_in_place() -> None:
    """A system that decides faster than it can be obeyed, stated as a fact
    rather than hidden behind an update count."""
    path = [
        point(ms(10), "101.00", anchors=(anchor("99.00", ms(10)),)),
        point(ms(20), "102.00", anchors=(anchor("99.50", ms(20)),)),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency(exchange_ns=10**12)).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.stop_updates > 0
    assert outcome.stop_updates_activated == 0


@pytest.mark.trace("REQ-WP-033")
def test_the_policy_is_shown_what_it_asked_for_not_what_landed() -> None:
    """Shown the active stop, a policy re-proposes the same movement at every
    point until the ack lands -- a reason histogram describing an engine with
    amnesia rather than a market with latency."""
    same = anchor("99.00", ms(10))
    path = [
        point(ms(10), "101.00", anchors=(same,)),
        point(ms(20), "101.00", anchors=(same,)),
        point(ms(30), "101.00", anchors=(same,)),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.stop_updates == 1


@pytest.mark.trace("REQ-WP-033")
def test_a_report_can_say_two_were_decided_and_one_landed() -> None:
    """The sentence §44A.27 exists to make sayable.

    Two decisions, the first acknowledged inside the path and the second still
    in flight when it ends. A counter that never incremented would satisfy the
    "nothing landed" test above and say nothing here.
    """
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(300), "101.00", anchors=(anchor("99.50", ms(300)),)),
        point(ms(400), "101.00"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.stop_updates == 2
    assert outcome.stop_updates_activated == 1


@pytest.mark.trace("REQ-WP-033")
def test_the_distance_to_the_stop_is_the_distance_to_the_active_one() -> None:
    """§44A's median and 95th-percentile stop distance are quantiles of this.

    Measured against the decided stop, they describe how close the position was
    to a level the exchange had not yet obeyed -- a risk statistic about a stop
    that was not protecting anything.

    Entry 100, R0 = 5. At .180 the decided stop is 98.85 and the active one is
    still the initial 95, so the distance from 100 is 1.0R, not 0.23R.
    """
    path = [
        point(ms(100), "101.00", anchors=(anchor("99.00", ms(100)),)),
        point(ms(180), "100.00"),
        point(ms(400), "94.00"),
    ]

    outcome = Replay(costs=free(), latency=ActivationLatency()).run_adaptive(
        long_position(), path, StopPolicy(cooldown_ns=0)
    )

    assert outcome.stop_distances_r[1] == pytest.approx(1.0)
