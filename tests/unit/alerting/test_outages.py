"""A feed going quiet is announced, and so is its coming back (REQ-WP-035)."""

from __future__ import annotations

import pytest

from channelflow.alerting import Dispatcher, OutageWatch
from channelflow.health import FeedHealth, HealthState

BASE_NS = 1788838800000000000
SECOND_NS = 1_000_000_000


class Recording:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, text: str, *, link: str) -> str:
        self.sent.append((text, link))
        return "ok"


def health(state: HealthState, *, at: int = 0, feed: str = "binance:BTCUSDT") -> FeedHealth:
    return FeedHealth(
        feed=feed,
        state=state,
        reason=f"{state.name.lower()} for the usual reasons",
        observed_at_ns=BASE_NS + at * SECOND_NS,
    )


def watching() -> tuple[OutageWatch, Recording, Dispatcher]:
    transport = Recording()
    dispatcher = Dispatcher(transport=transport)
    return (
        OutageWatch(dispatcher=dispatcher, chart_base_url="https://charts.example"),
        transport,
        dispatcher,
    )


# --- transitions, not states -------------------------------------------------


@pytest.mark.trace("REQ-WP-035")
def test_a_feed_turning_bad_is_announced_once() -> None:
    watch, transport, _ = watching()

    watch.observe(health(HealthState.STALE, at=0))

    assert len(transport.sent) == 1


@pytest.mark.trace("REQ-WP-035")
def test_the_same_bad_state_seen_again_says_nothing() -> None:
    """A feed hovering at a threshold alerts on every observation, and a channel
    that cries constantly loses the outage as thoroughly as silence would."""
    watch, transport, _ = watching()

    watch.observe(health(HealthState.STALE, at=0))
    watch.observe(health(HealthState.STALE, at=1))
    watch.observe(health(HealthState.STALE, at=2))

    assert len(transport.sent) == 1


@pytest.mark.trace("REQ-WP-035")
def test_getting_worse_is_a_new_fact() -> None:
    watch, transport, _ = watching()

    watch.observe(health(HealthState.DEGRADED, at=0))
    watch.observe(health(HealthState.INVALID, at=1))

    assert len(transport.sent) == 2


@pytest.mark.trace("REQ-WP-035")
def test_a_feed_first_seen_good_says_nothing() -> None:
    """Announcing a recovery from nothing reports an outage that never
    happened."""
    watch, transport, _ = watching()

    record = watch.observe(health(HealthState.GOOD, at=0))

    assert transport.sent == []
    assert record is None


@pytest.mark.trace("REQ-WP-035")
def test_a_feed_first_seen_bad_is_announced() -> None:
    """Waiting for a prior good state would stay silent through an outage that
    began before the process did."""
    watch, transport, _ = watching()

    watch.observe(health(HealthState.INVALID, at=0))

    assert len(transport.sent) == 1


# --- the recovery is half the requirement ------------------------------------


@pytest.mark.trace("REQ-WP-035")
def test_coming_back_is_announced_with_how_long_it_was_bad() -> None:
    """Silence after a failure notice reads as "still down" and as "nobody is
    watching" equally well."""
    watch, transport, _ = watching()

    watch.observe(health(HealthState.STALE, at=0))
    watch.observe(health(HealthState.GOOD, at=90))

    text = transport.sent[1][0]
    assert "RECOVERED" in text
    assert "90" in text


@pytest.mark.trace("REQ-WP-035")
def test_a_recovery_nobody_was_told_about_is_not_announced() -> None:
    watch, transport, _ = watching()

    watch.observe(health(HealthState.GOOD, at=0))
    watch.observe(health(HealthState.GOOD, at=1))

    assert transport.sent == []


@pytest.mark.trace("REQ-WP-035")
def test_a_duration_of_zero_is_a_duration() -> None:
    """Bad and good within one instant. True, and not the same as absent."""
    watch, transport, _ = watching()

    watch.observe(health(HealthState.STALE, at=7))
    watch.observe(health(HealthState.GOOD, at=7))

    assert "0" in transport.sent[1][0]


@pytest.mark.trace("REQ-WP-035")
def test_two_feeds_are_watched_apart() -> None:
    watch, transport, _ = watching()

    watch.observe(health(HealthState.STALE, at=0, feed="binance:BTCUSDT"))
    watch.observe(health(HealthState.STALE, at=0, feed="binance:ETHUSDT"))

    assert len(transport.sent) == 2


# --- not mistakable for a trade ----------------------------------------------


@pytest.mark.trace("REQ-WP-035")
def test_an_operational_alert_shares_no_header_with_a_trading_one() -> None:
    """They travel the same wire to the same reader, who acts on one and
    investigates the other."""
    watch, transport, _ = watching()

    watch.observe(health(HealthState.INVALID, at=0))

    text = transport.sent[0][0]
    assert "SETUP" not in text
    assert "STOP UPDATED" not in text
    assert "DATA" in text


@pytest.mark.trace("REQ-WP-035")
def test_the_message_names_the_feed_the_state_and_the_reason() -> None:
    watch, transport, _ = watching()

    watch.observe(health(HealthState.STALE, at=0))

    text = transport.sent[0][0]
    assert "binance:BTCUSDT" in text
    assert "STALE" in text
    assert "for the usual reasons" in text


@pytest.mark.trace("REQ-WP-035")
def test_the_notification_id_says_which_state_it_announced() -> None:
    """ADR-017: derived, never generated -- and derived from enough.

    A feed degrading and then failing at the same observation instant are two
    different announcements. An id that named only the feed would give both the
    same identity, and any dedupe reading it would drop the second.
    """
    from channelflow.alerting import OutageAlert

    def alert_for(state: HealthState) -> OutageAlert:
        return OutageAlert(
            health=health(state, at=0),
            previous=HealthState.GOOD,
            chart_base_url="https://charts.example",
        )

    assert alert_for(HealthState.DEGRADED).notification_id != (
        alert_for(HealthState.INVALID).notification_id
    )
    assert (
        alert_for(HealthState.INVALID).notification_id
        == alert_for(HealthState.INVALID).notification_id
    )


@pytest.mark.trace("REQ-WP-035")
def test_operational_alerts_are_audited_like_everything_else() -> None:
    watch, _, dispatcher = watching()

    record = watch.observe(health(HealthState.STALE, at=0))

    assert record is not None
    assert record.status == "delivered"
    assert dispatcher.audit[0].symbol == "binance:BTCUSDT"
