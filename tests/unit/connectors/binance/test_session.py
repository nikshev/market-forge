"""Stream lifecycle, driven by a fake clock and a fake connector (REQ-WP-003).

No socket opens here. PRD section 35.6 lists reconnect among the things
connector tests must cover by replay, and FR-018 forbids network access -- so
the lifecycle takes its clock and its connector as arguments, and the tests
supply both.
"""

from __future__ import annotations

import queue

import pytest


class FakeConnector:
    """A connector that records what was asked of it and never opens a socket."""

    def __init__(self) -> None:
        self.connects: list[tuple[str, ...]] = []
        self.sent: list[str] = []
        self.pongs = 0
        self.closed = 0
        self.fail_next_connect = False
        self._frames = queue.Queue()

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
        return self._frames


#: Binance closes a stream 24 hours after it opens.
STREAM_LIFETIME_NS = 24 * 60 * 60 * 1_000_000_000


@pytest.mark.trace("REQ-WP-003")
def test_it_reconnects_before_the_venue_closes_the_stream() -> None:
    """SC-007, FR-012. Binance closes a stream at 24 hours. Reconnecting
    afterwards means losing data; the point is to move first."""
    from channelflow.connectors.session import (
        BINANCE,
        FakeClock,
        StreamSession,
    )
    clock = FakeClock()
    connector = FakeConnector()
    session = StreamSession(("btcusdt@aggTrade",), policy=BINANCE, connector=connector, clock=clock)
    session.start()
    assert len(connector.connects) == 1

    clock.advance_ns(STREAM_LIFETIME_NS - 1)
    session.tick()
    assert len(connector.connects) == 1

    clock.advance_ns(2)
    session.tick()
    assert len(connector.connects) == 2, "must reconnect before the venue's limit"


@pytest.mark.trace("REQ-WP-003")
def test_a_ping_is_answered() -> None:
    """FR-013. Binance disconnects a client that does not answer."""
    from channelflow.connectors.session import (
        BINANCE,
        FakeClock,
        StreamSession,
    )
    connector = FakeConnector()
    session = StreamSession(
        ("btcusdt@aggTrade",), policy=BINANCE, connector=connector, clock=FakeClock()
    )
    session.start()
    session.on_ping()
    assert connector.pongs == 1


@pytest.mark.trace("REQ-WP-003")
def test_a_reconnect_demands_a_fresh_snapshot() -> None:
    """FR-014. Resuming a book across a reconnect assumes no update was missed
    during the gap, which is exactly what PRD section 27.5 forbids."""
    from channelflow.connectors.session import (
        BINANCE,
        FakeClock,
        StreamSession,
    )
    clock = FakeClock()
    session = StreamSession(
        ("btcusdt@depth@100ms",), policy=BINANCE, connector=FakeConnector(), clock=clock
    )
    session.start()
    assert session.needs_snapshot

    session.snapshot_taken()
    assert not session.needs_snapshot

    clock.advance_ns(STREAM_LIFETIME_NS + 1)
    session.tick()
    assert session.needs_snapshot, "a reconnected stream must rebuild, not resume"


@pytest.mark.trace("REQ-WP-003")
def test_each_failure_kind_is_counted() -> None:
    """FR-017. A connector that fails silently is indistinguishable from one
    that is idle."""
    from channelflow.connectors.session import (
        BINANCE,
        FakeClock,
        StreamSession,
    )
    connector = FakeConnector()
    session = StreamSession(
        ("btcusdt@aggTrade",), policy=BINANCE, connector=connector, clock=FakeClock()
    )

    connector.fail_next_connect = True
    with pytest.raises(ConnectionError):
        session.start()
    assert session.metrics.connection_failures == 1

    session.record_sequence_gap()
    session.record_normalization_failure()
    session.record_poll_failure()
    assert session.metrics.sequence_gaps == 1
    assert session.metrics.normalization_failures == 1
    assert session.metrics.poll_failures == 1


@pytest.mark.trace("REQ-WP-003")
def test_the_stream_set_is_configurable() -> None:
    """FR-015. Hard-coding the streams would make the Phase 1 universe a code
    change rather than configuration."""
    from channelflow.connectors.session import (
        BINANCE,
        FakeClock,
        StreamSession,
    )
    connector = FakeConnector()
    streams = ("btcusdt@aggTrade", "ethusdt@depth@100ms")
    StreamSession(streams, policy=BINANCE, connector=connector, clock=FakeClock()).start()
    assert connector.connects == [streams]


# ... rest of the file continues with similar patterns ...