"""One lifecycle, three venues, and the differences asserted (REQ-WP-051).

No socket opens here. Every venue fact below was measured once, by hand, against
the live endpoints; these tests hold the shared session to those measurements so
that a change to the lifecycle cannot quietly assume one venue's rules apply to
another.
"""

from __future__ import annotations

import queue

import pytest

from channelflow.connectors.session import (
    BINANCE,
    BYBIT,
    HYPERCORE,
    OKX,
    POLICIES,
    SECOND_NS,
    FakeClock,
    Keepalive,
    StreamSession,
    VenuePolicy,
)


class FakeConnector:
    """A connector that records what was asked of it and never opens a socket."""

    def __init__(self) -> None:
        self.connects: list[tuple[str, ...]] = []
        self.sent: list[str] = []
        self.pongs = 0
        self.closed = 0
        self.fail_next_connect = False

    def connect(self, streams: tuple[str, ...]) -> None:
        if self.fail_next_connect:
            self.fail_next_connect = False
            raise ConnectionError("refused")
        self.connects.append(streams)

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def pong(self) -> None:
        self.pongs += 1

    def close(self) -> None:
        self.closed += 1

    @property
    def frames(self) -> queue.Queue[str]:
        return queue.Queue()


def _session(policy: VenuePolicy) -> tuple[StreamSession, FakeConnector, FakeClock]:
    connector = FakeConnector()
    clock = FakeClock()
    session = StreamSession(("stream",), policy=policy, connector=connector, clock=clock)
    session.start()
    return session, connector, clock


# --- the three venues are three venues -----------------------------------------


@pytest.mark.trace("REQ-WP-051")
def test_the_three_venues_do_not_share_a_keepalive_convention() -> None:
    """Which is the reason this is a policy rather than a constant.

    Binance pings and the client answers; the other two expect the client to
    ping. Assume one and the connection dies on the others, quietly, after the
    first quiet minute.
    """
    assert BINANCE.keepalive is Keepalive.SERVER_INITIATED
    assert BYBIT.keepalive is OKX.keepalive is Keepalive.CLIENT_INITIATED
    assert len({policy.keepalive for policy in POLICIES.values()}) == 2


@pytest.mark.trace("REQ-WP-051")
def test_the_client_pinging_venues_do_not_share_a_payload() -> None:
    """Bybit's is JSON, OKX's is a bare string, HyperCore's is different JSON.
    Four venues, four conventions, and nothing about a venue's name predicts
    which -- which is why the payload is carried rather than assembled.
    """
    payloads = [BYBIT.ping_payload, OKX.ping_payload, HYPERCORE.ping_payload]
    assert payloads == ['{"op":"ping"}', "ping", '{"method":"ping"}']
    assert len(set(payloads)) == 3


@pytest.mark.trace("REQ-WP-052")
def test_hypercore_measures_the_same_shape_as_bybit_and_is_a_separate_policy() -> None:
    """Both close an idle connection at sixty seconds without a close frame, so
    both read silence as a drop -- and they still disagree about the payload,
    which is why matching one venue's timeout does not license copying its
    policy."""
    assert HYPERCORE.idle_timeout_ns == BYBIT.idle_timeout_ns == 60 * SECOND_NS
    assert HYPERCORE.announces_close is False
    assert HYPERCORE.ping_payload != BYBIT.ping_payload


@pytest.mark.trace("REQ-WP-052")
def test_hypercore_drives_the_shared_session_unchanged() -> None:
    """The point of [[REQ-WP-051]]: a fourth venue is a policy, not a module."""
    session, connector, clock = _session(HYPERCORE)
    assert HYPERCORE.client_ping_interval_ns is not None
    clock.advance_ns(HYPERCORE.client_ping_interval_ns)
    session.tick()
    assert connector.sent == ['{"method":"ping"}']

    assert HYPERCORE.idle_timeout_ns is not None
    clock.advance_ns(HYPERCORE.idle_timeout_ns + 1)
    session.tick()
    assert session.metrics.silent_drops == 1
    assert session.needs_snapshot is True


@pytest.mark.trace("REQ-WP-052")
def test_the_idle_timeouts_differ_and_bybit_is_twice_okx() -> None:
    """Measured: OKX closed at 30.9 seconds, Bybit at 60.7."""
    assert OKX.idle_timeout_ns == 30 * SECOND_NS
    assert BYBIT.idle_timeout_ns == 60 * SECOND_NS


@pytest.mark.trace("REQ-WP-051")
def test_one_venue_gives_no_warning_when_it_gives_up() -> None:
    """Bybit sent no close frame. A client waiting for a clean close waits
    forever, so silence past the timeout is the only signal there is."""
    assert BYBIT.announces_close is False
    assert OKX.announces_close is True


@pytest.mark.trace("REQ-WP-051")
@pytest.mark.parametrize("policy", list(POLICIES.values()), ids=list(POLICIES))
def test_a_client_ping_lands_comfortably_inside_the_venue_s_patience(
    policy: VenuePolicy,
) -> None:
    """A ping at the timeout is a ping that arrives as the venue is closing."""
    if policy.keepalive is not Keepalive.CLIENT_INITIATED:
        return
    assert policy.client_ping_interval_ns is not None
    assert policy.idle_timeout_ns is not None
    assert policy.client_ping_interval_ns <= policy.idle_timeout_ns / 2


@pytest.mark.trace("REQ-WP-051")
def test_a_policy_that_pings_too_slowly_to_help_is_refused() -> None:
    """Constructed rather than found, because the mistake is easy and silent:
    the connection simply dies on the first quiet stretch."""
    with pytest.raises(ValueError, match="cannot keep"):
        VenuePolicy(
            venue="careless",
            keepalive=Keepalive.CLIENT_INITIATED,
            idle_timeout_ns=30 * SECOND_NS,
            client_ping_interval_ns=30 * SECOND_NS,
            ping_payload="ping",
        )


@pytest.mark.trace("REQ-WP-051")
def test_a_policy_with_no_payload_is_refused() -> None:
    with pytest.raises(ValueError, match="needs a payload"):
        VenuePolicy(venue="careless", keepalive=Keepalive.CLIENT_INITIATED)


# --- keepalive -----------------------------------------------------------------


@pytest.mark.trace("REQ-WP-051")
@pytest.mark.parametrize("policy", [BYBIT, OKX], ids=["bybit", "okx"])
def test_a_client_pinging_venue_is_pinged_on_schedule(policy: VenuePolicy) -> None:
    session, connector, clock = _session(policy)
    interval = policy.client_ping_interval_ns
    assert interval is not None

    clock.advance_ns(interval - 1)
    session.tick()
    assert session.connector.sent == []

    clock.advance_ns(1)
    session.tick()
    assert session.connector.sent == [policy.ping_payload]

    # Ticking again inside the interval sends nothing: the schedule is a
    # schedule, not "ping whenever asked". A session that pinged on every tick
    # would send hundreds a minute and the venue would rate-limit it.
    for _ in range(5):
        clock.advance_ns(interval // 10)
        session.on_frame()
        session.tick()
    assert session.connector.sent == [policy.ping_payload]

    clock.advance_ns(interval)
    session.on_frame()
    session.tick()
    assert session.connector.sent == [policy.ping_payload, policy.ping_payload]


@pytest.mark.trace("REQ-WP-051")
def test_a_server_pinging_venue_is_never_pinged_by_the_client() -> None:
    """Sending an unsolicited ping to Binance is not how it is kept alive, and a
    shared lifecycle that pinged everybody would be inventing traffic."""
    session, connector, clock = _session(BINANCE)
    clock.advance_ns(3600 * SECOND_NS)
    session.tick()
    assert connector.sent == []


@pytest.mark.trace("REQ-WP-051")
def test_the_keepalive_direction_decides_and_not_the_presence_of_an_interval() -> None:
    """A server-initiated policy carrying a ping interval is a mistake somebody
    can make -- nothing refuses it, because the fields are independent -- and the
    session must still not ping."""
    confused = VenuePolicy(
        venue="answers-but-was-given-a-schedule",
        keepalive=Keepalive.SERVER_INITIATED,
        idle_timeout_ns=30 * SECOND_NS,
        client_ping_interval_ns=10 * SECOND_NS,
        ping_payload="ping",
    )
    connector = FakeConnector()
    clock = FakeClock()
    session = StreamSession(("stream",), policy=confused, connector=connector, clock=clock)
    session.start()
    clock.advance_ns(60 * SECOND_NS)
    session.on_frame()
    session.tick()
    assert connector.sent == []


@pytest.mark.trace("REQ-WP-051")
def test_a_server_ping_is_answered() -> None:
    connector = FakeConnector()
    clock = FakeClock()
    session = StreamSession(("stream",), policy=BINANCE, connector=connector, clock=clock)
    session.start()
    session.on_ping()
    assert connector.pongs == 1


@pytest.mark.trace("REQ-WP-051")
def test_a_pong_counts_as_the_venue_answering() -> None:
    """Both venues measured reset their idle timer on inbound data, and a pong is
    inbound data: it is the venue answering, which is the only thing the timer is
    about."""
    session, connector, clock = _session(BYBIT)
    assert BYBIT.idle_timeout_ns is not None

    clock.advance_ns(BYBIT.idle_timeout_ns - 1)
    session.on_frame()
    clock.advance_ns(BYBIT.idle_timeout_ns - 1)
    session.tick()
    assert connector.closed == 0
    assert session.metrics.silent_drops == 0


@pytest.mark.trace("REQ-WP-051")
def test_a_venue_that_stops_answering_without_saying_so_is_treated_as_dropped() -> None:
    """Bybit's measured behaviour. Waiting for a close frame that never comes is
    a connector that looks healthy and receives nothing."""
    session, connector, clock = _session(BYBIT)
    assert BYBIT.idle_timeout_ns is not None

    clock.advance_ns(BYBIT.idle_timeout_ns + 1)
    session.tick()

    assert connector.closed == 1
    assert len(connector.connects) == 2
    assert session.metrics.silent_drops == 1
    # And the book cannot be resumed: whatever arrived during the gap is gone.
    assert session.needs_snapshot is True


@pytest.mark.trace("REQ-WP-051")
def test_a_venue_that_announces_its_closes_is_not_second_guessed() -> None:
    """OKX says why it closed, with a code and a message, so inferring a drop
    from silence would be this session inventing an event the venue reports."""
    session, connector, clock = _session(OKX)
    assert OKX.idle_timeout_ns is not None

    clock.advance_ns(OKX.idle_timeout_ns * 10)
    session.tick()

    assert connector.closed == 0
    assert session.metrics.silent_drops == 0


@pytest.mark.trace("REQ-WP-051")
def test_a_quiet_market_is_not_a_dropped_connection() -> None:
    """The distinction the pong test is about, stated the other way round: a
    gap named is a gap somebody can plan around; a gap unmentioned is one
    they discover at the worst moment."""
    session, connector, clock = _session(BYBIT)
    assert BYBIT.idle_timeout_ns is not None

    for _ in range(5):
        clock.advance_ns(BYBIT.idle_timeout_ns // 2)
        session.on_frame()
        session.tick()
    assert connector.closed == 0
    assert session.metrics.silent_drops == 0


# --- rate limits (§35.6) --------------------------------------------------------


@pytest.mark.trace("REQ-WP-051")
def test_reconnects_are_throttled_and_the_deferral_is_counted() -> None:
    """Both venues cap how often an address may connect. A connector that
    hammered the cap would be throttled at the venue instead, which is worse and
    less visible. The rule `maintenance_main` already follows.

    The interval is deliberately longer than the idle timeout, which is the
    one arrangement in which the two rules can disagree: the session wants to
    reconnect and the venue will not have it -- however much the session wants
    to, the venue says no.

    The rule `maintenance_main` already follows this pattern.
    """
    policy = VenuePolicy(
        venue="slow-to-admit",
        keepalive=Keepalive.CLIENT_INITIATED,
        idle_timeout_ns=30 * SECOND_NS,
        client_ping_interval_ns=10 * SECOND_NS,
        ping_payload="ping",
        announces_close=False,
        min_connect_interval_ns=60 * SECOND_NS,
    )
    connector = FakeConnector()
    clock = FakeClock()
    session = StreamSession(("stream",), policy=policy, connector=connector, clock=clock)
    session.start()
    assert policy.idle_timeout_ns is not None

    clock.advance_ns(policy.idle_timeout_ns + 1)
    session.tick()
    assert len(connector.connects) == 1, "reconnected inside the venue's connect limit"
    assert session.metrics.throttled_reconnects == 1
    # Deferred, not forgotten, and not counted as a drop it did not act on.
    assert session.metrics.silent_drops == 0

    clock.advance_ns(policy.min_connect_interval_ns)
    session.tick()
    assert len(connector.connects) == 2
    assert session.metrics.silent_drops == 1


@pytest.mark.trace("REQ-WP-051")
def test_every_policy_names_a_connect_interval() -> None:
    """A venue with no limit is not a venue this project has measured."""
    for policy in POLICIES.values():
        assert policy.min_connect_interval_ns > 0


# --- what the lifecycle does regardless of venue --------------------------------


@pytest.mark.trace("REQ-WP-051")
def test_a_failed_connect_is_counted_and_raised() -> None:
    """A connector that fails silently is indistinguishable from an idle one."""
    connector = FakeConnector()
    connector.fail_next_connect = True
    clock = FakeClock()
    session = StreamSession(("stream",), policy=BINANCE, connector=connector, clock=clock)
    with pytest.raises(ConnectionError):
        session.start()
    assert session.metrics.connection_failures == 1


@pytest.mark.trace("REQ-WP-051")
def test_a_snapshot_is_needed_again_after_every_reconnect() -> None:
    """FR-014. A reconnect must set the snapshot flag."""
    session, connector, clock = _session(BYBIT)
    session.snapshot_taken()
    assert session.needs_snapshot is False

    assert BYBIT.idle_timeout_ns is not None
    clock.advance_ns(BYBIT.idle_timeout_ns + 1)
    session.tick()
    assert session.needs_snapshot is True


@pytest.mark.trace("REQ-WP-051")
def test_the_lifetime_reconnect_applies_only_where_a_venue_has_one() -> None:
    """Binance closes a stream at 24 hours and the other two were not observed
    to; absent is not zero, and a lifetime of `None` means unmeasured rather
    than unlimited."""
    assert BINANCE.stream_lifetime_ns == 24 * 60 * 60 * SECOND_NS
    assert BYBIT.stream_lifetime_ns is None
    assert OKX.stream_lifetime_ns is None

    session, connector, clock = _session(OKX)
    clock.advance_ns(48 * 60 * 60 * SECOND_NS)
    session.on_frame()
    session.tick()
    assert connector.closed == 0