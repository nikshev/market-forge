"""A connection that ends is reopened, whatever ended it and whichever venue it was (REQ-WP-078).

# @trace: REQ-WP-078

`StreamSession.tick` reconnected on silence only when the venue did *not* announce a
close -- Bybit alone. Binance and OKX were assumed to say so when they gave up, and
nothing in the connectors turned what they said into anything: the reader thread simply
ended. A Binance daemon whose socket died stayed `Up` for four days with no feed.

Every test here uses a policy with `announces_close=True`, because that is the shape the
old rule ignored. A test on Bybit would have passed against the broken code.
"""

from __future__ import annotations

import logging
import math

import pytest

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import (
    BINANCE,
    OKX,
    SECOND_NS,
    FakeClock,
    StreamSession,
    VenuePolicy,
)
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore, read_frames
from channelflow.pipeline.ingest import IngestDaemon

from .fakes import ControllableConnector

SESSION_LOG = "channelflow.connectors.session"


def _session(
    policy: VenuePolicy = OKX,
) -> tuple[StreamSession, ControllableConnector, FakeClock]:
    clock = FakeClock(1_000 * SECOND_NS)
    connector = ControllableConnector()
    connector.now_ns = clock.now_ns
    session = StreamSession(("stream",), policy=policy, connector=connector, clock=clock)
    session.start()
    return session, connector, clock


def _records(caplog: pytest.LogCaptureFixture, *, at_least: int) -> list[logging.LogRecord]:
    """From the session's logger only. `caplog` collects every logger, and other tests
    in the suite leave reader threads that log on their own schedule."""
    return [r for r in caplog.records if r.name == SESSION_LOG and r.levelno >= at_least]


# --- a dead reader ------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_a_reader_that_ended_without_a_close_frame_is_reconnected() -> None:
    """Today's shape for Binance and OKX, and the one `tick` ignored."""
    assert OKX.announces_close is True
    session, connector, clock = _session(OKX)

    connector.kill()
    clock.advance_ns(2 * SECOND_NS)
    session.tick()

    assert connector.closed == 1
    assert len(connector.connects) == 2
    assert session.metrics.dead_readers == 1, "a reader that ended must be counted as one"
    assert session.metrics.silent_drops == 0, "and it was not silence"


@pytest.mark.trace("REQ-WP-078")
def test_a_healthy_connection_is_left_alone() -> None:
    session, connector, clock = _session(OKX)

    for _ in range(100):
        clock.advance_ns(SECOND_NS // 5)
        session.on_frame()
        session.tick()

    assert connector.closed == 0 and len(connector.connects) == 1


# --- silence ------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("policy", [BINANCE, OKX], ids=["binance", "okx"])
def test_a_quiet_feed_is_reconnected_even_where_the_venue_announces_its_closes(
    policy: VenuePolicy,
) -> None:
    """The rewritten `test_a_venue_that_announces_its_closes_is_not_second_guessed`.

    That test held that inferring a drop from silence would be "inventing an event the
    venue reports". The venue reports it; nothing read the report. Binance went silent
    on 2026-09-28 and the daemon first said so two days later.
    """
    assert policy.announces_close is True and policy.max_silence_ns is not None
    session, connector, clock = _session(policy)

    clock.advance_ns(policy.max_silence_ns)  # elapsed == limit: not yet past it
    session.tick()
    assert connector.closed == 0

    clock.advance_ns(1)
    session.tick()
    assert connector.closed == 1 and len(connector.connects) == 2
    assert session.metrics.silent_drops == 1


@pytest.mark.trace("REQ-WP-078")
def test_the_silence_limit_is_not_the_venues_idle_timeout() -> None:
    """Binance's 24 hours is a stream lifetime. Doubled and borrowed as a silence
    threshold it was 48 hours, and a feed silent since 09-28 07:45 could not have been
    reported before 09-30 07:45."""
    assert BINANCE.idle_timeout_ns is None
    assert BINANCE.max_silence_ns is not None and BINANCE.max_silence_ns < 5 * 60 * SECOND_NS


@pytest.mark.trace("REQ-WP-078")
def test_the_stream_lifetime_reconnects_a_healthy_binance_connection() -> None:
    assert BINANCE.stream_lifetime_ns == 24 * 60 * 60 * SECOND_NS
    session, connector, clock = _session(BINANCE)

    clock.advance_ns(BINANCE.stream_lifetime_ns - 1)
    session.on_frame()
    session.tick()
    assert connector.closed == 0

    clock.advance_ns(1)
    session.on_frame()
    session.tick()
    assert connector.closed == 1 and len(connector.connects) == 2


# --- the log ------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_one_outage_is_one_warning_on_entry_and_one_info_on_recovery(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session, connector, clock = _session(OKX)
    caplog.set_level(logging.INFO)

    connector.kill()
    clock.advance_ns(2 * SECOND_NS)
    session.tick()  # down, one attempt, the connection comes back
    for _ in range(500):  # then 500 ordinary ticks with the feed alive
        clock.advance_ns(SECOND_NS // 5)
        session.on_frame()
        session.tick()

    warnings = _records(caplog, at_least=logging.WARNING)
    infos = [r for r in _records(caplog, at_least=logging.INFO) if r.levelno == logging.INFO]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]
    assert len(infos) == 1 and "recover" in infos[0].getMessage().lower()


@pytest.mark.trace("REQ-WP-078")
def test_a_persisting_silence_does_not_log_on_every_tick(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The old daemon warned on every step, five a second, for as long as it lasted.

    1,000 ticks of 200 ms is 200 seconds: about three attempts against OKX's 60-second
    limit, each of which may log, and none of the 997 other ticks may.
    """
    session, connector, clock = _session(OKX)
    caplog.set_level(logging.INFO)

    for _ in range(1000):
        clock.advance_ns(SECOND_NS // 5)
        session.tick()

    attempts = len(connector.attempts) - 1
    assert attempts >= 3
    assert len(_records(caplog, at_least=logging.WARNING)) <= 1 + math.floor(math.log2(attempts))


# --- refusal and backoff ------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_attempts_back_off_and_a_refused_connect_does_not_escape_tick() -> None:
    """`NotConnected` from Binance's `connect()` used to leave `tick` and end the daemon."""
    session, connector, clock = _session(OKX)
    connector.kill()
    connector.refuse_next = 10_000
    base = OKX.min_connect_interval_ns

    for _ in range(3_000):  # five minutes at 100 ms; `tick` raising fails the test
        clock.advance_ns(SECOND_NS // 10)
        session.tick()

    times = connector.attempts[1:]  # [0] is the first, successful, connect
    gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
    assert len(gaps) >= 6
    for index, gap in enumerate(gaps, start=1):
        expected = min(base * 2 ** (index - 1), OKX.max_connect_backoff_ns)
        assert gap >= expected, (index, gap, expected)
        assert gap < expected + SECOND_NS // 5, (index, gap, expected)
    assert session.metrics.connection_failures >= len(gaps)


@pytest.mark.trace("REQ-WP-078")
def test_two_hundred_refusals_are_a_handful_of_log_lines_and_one_recovery(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session, connector, clock = _session(OKX)
    connector.kill()
    connector.refuse_next = 10_000
    caplog.set_level(logging.INFO)

    # Bounded: a session that never retries must fail this test, not hang it.
    for _ in range(20_000):
        if len(connector.attempts) >= 201:
            break
        clock.advance_ns(SECOND_NS)
        session.tick()
    assert len(connector.attempts) >= 201, "the session stopped retrying"

    refusals = len(connector.attempts) - 1
    assert len(_records(caplog, at_least=logging.WARNING)) <= 12

    connector.refuse_next = 0
    for _ in range(200):
        if len(connector.connects) >= 2:
            break
        clock.advance_ns(SECOND_NS)
        session.tick()
    assert len(connector.connects) >= 2, "the session never connected once the venue relented"
    session.on_frame()  # the feed is back: this, not `connect()` returning, is recovery

    infos = [r for r in _records(caplog, at_least=logging.INFO) if r.levelno == logging.INFO]
    assert len(infos) == 1
    assert f"{refusals + 1} attempt" in infos[0].getMessage()


@pytest.mark.trace("REQ-WP-078")
def test_a_connect_that_returns_and_a_reader_that_dies_again_keeps_its_backoff() -> None:
    """Bybit's and OKX's `connect()` only starts a thread, so returning proves nothing.
    The count must survive it, or a venue that accepts the socket and drops it would be
    retried at the minimum interval for ever."""
    session, connector, clock = _session(OKX)
    connector.kill()
    connector.die_after_connect = True

    for _ in range(3_000):
        clock.advance_ns(SECOND_NS // 10)
        session.tick()

    times = connector.attempts[1:]
    gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
    assert len(gaps) >= 6
    assert gaps[-1] >= OKX.max_connect_backoff_ns, "the backoff reset each time connect() returned"
    assert gaps == sorted(gaps), "the delay shrank between attempts"


# --- what the daemon keeps across a reconnect ---------------------------------


@pytest.mark.trace("REQ-WP-078")
def test_a_reconnect_in_the_middle_of_a_minute_loses_nothing_the_daemon_holds(
    tmp_path,
) -> None:
    """Through `IngestDaemon`, not the session alone.

    The spec says the bars builder and the archive buffer outlive the socket. An
    implementation that rebuilt the daemon's collaborators on reconnect would pass every
    other test in this file and lose a minute of frames each time it reconnected.
    """
    minute = 1_790_000_040 * SECOND_NS  # forty seconds into a minute, well inside it
    clock = FakeClock(minute)
    connector = ControllableConnector()
    connector.now_ns = clock.now_ns
    archive = FrameArchive(
        store=LocalObjectStore(root=tmp_path), venue="okx", symbol="BTC-USDT-SWAP"
    )
    daemon = IngestDaemon(
        session=StreamSession(
            ("trades.BTC-USDT-SWAP",), policy=OKX, connector=connector, clock=clock
        ),
        connector=connector,
        archive=archive,
        builder=BarBuilder(timeframe_ns=SECOND_NS, on_final=lambda bar: None),
        venue="okx",
        now_ns=clock.now_ns,
    )
    daemon.start()
    before = [f"before-{n}" for n in range(5)]
    after = [f"after-{n}" for n in range(5)]

    for frame in before:
        connector.push(frame)
    daemon.step()
    connector.kill()
    clock.advance_ns(2 * SECOND_NS)
    daemon.step()  # the session notices and reconnects
    assert len(connector.connects) == 2, "the session did not reconnect"
    for frame in after:
        connector.push(frame)
    daemon.step()
    daemon.stop()

    assert daemon.archive is archive
    objects = list(tmp_path.rglob("*.jsonl.gz"))
    assert len(objects) == 1, [p.name for p in objects]
    held = [frame for _, frame in read_frames(objects[0].read_bytes())]
    assert held == before + after


# --- found live, not by any test above -----------------------------------------------
#
# The first live proof of the reconnect (dropping only a daemon's websocket traffic) killed
# the process. The reader ended, the session began to reconnect, and before the new socket
# had opened the client ping went to the *old*, closed one and raised
# `ConnectionClosedError` out of `tick` and out of the whole loop. Every fake in this file
# has a `send` that works, which is why none of it saw this.


@pytest.mark.trace("REQ-WP-078")
def test_a_ping_that_cannot_be_sent_does_not_end_the_loop() -> None:
    session, connector, clock = _session(OKX)
    connector.fail_send = True

    for _ in range(300):  # sixty seconds of 200 ms ticks, the feed alive throughout
        clock.advance_ns(SECOND_NS // 5)
        session.on_frame()
        session.tick()  # raising here fails the test: that is the crash

    assert connector.send_attempts, "the ping was never tried, so nothing was tested"


@pytest.mark.trace("REQ-WP-078")
def test_a_failing_ping_is_tried_once_an_interval_and_not_on_every_tick(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If a failed ping did not advance the ping clock it would be retried at 5 Hz, which is
    the log volume this requirement exists to remove."""
    session, connector, clock = _session(OKX)
    connector.fail_send = True
    caplog.set_level(logging.INFO)

    for _ in range(300):
        clock.advance_ns(SECOND_NS // 5)
        session.on_frame()
        session.tick()

    interval = OKX.client_ping_interval_ns
    assert interval is not None
    expected = (60 * SECOND_NS) // interval
    assert len(connector.send_attempts) <= expected + 1, len(connector.send_attempts)
    assert len(_records(caplog, at_least=logging.WARNING)) <= expected + 1
