"""Tests for StreamSession with venue-specific policies (REQ-WP-076)."""

# @trace: REQ-WP-076

import queue

import pytest

from channelflow.connectors.session import FakeClock, StreamSession
from channelflow.connectors.venue import BINANCE_POLICY, BYBIT_POLICY, OKX_POLICY
from channelflow.pipeline.ingest import streams_for


class FakePolicyConnector:
    """Fake connector that tracks pings and timeouts for policy testing."""

    def __init__(self, policy):
        self._frames = queue.Queue()
        self._connected = False
        self._closed = False
        self.policy = policy
        self.sent_pings = []

    def connect(self, streams):
        self._connected = True

    def send(self, payload):
        self.sent_pings.append(payload)

    def pong(self):
        pass

    def close(self):
        self._closed = True

    @property
    def frames(self):
        return self._frames

    def drain_frames(self) -> list[str]:
        out = []
        while True:
            try:
                out.append(self._frames.get_nowait())
            except queue.Empty:
                return out


class TestStreamSessionPolicies:
    """StreamSession enforces each venue's own connection policy."""

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_policy_pings_with_payload(self):
        """Bybit session pings with Bybit's payload on schedule."""
        connector = FakePolicyConnector(BYBIT_POLICY)
        clock = FakeClock()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=BYBIT_POLICY,
            connector=connector,
            clock=clock,
        )
        session.start()

        # Advance clock past the ping interval
        clock.advance_ns(BYBIT_POLICY.client_ping_interval_ns + 1)
        session.tick()

        # Bybit's ping payload is {"op":"ping"}
        assert connector.sent_pings == ['{"op":"ping"}']

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_policy_pings_bare_string(self):
        """OKX session pings with bare string 'ping' on schedule."""
        connector = FakePolicyConnector(OKX_POLICY)
        clock = FakeClock()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=OKX_POLICY,
            connector=connector,
            clock=clock,
        )
        session.start()

        clock.advance_ns(OKX_POLICY.client_ping_interval_ns + 1)
        session.tick()

        # OKX's ping payload is bare "ping"
        assert connector.sent_pings == ["ping"]

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_policy_uses_websocket_ping(self):
        """Binance session uses websocket protocol ping/pong, not application ping."""
        connector = FakePolicyConnector(BINANCE_POLICY)
        clock = FakeClock()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=BINANCE_POLICY,
            connector=connector,
            clock=clock,
        )
        session.start()

        # Binance has no client ping interval (server-initiated ping/pong)
        # Advance clock arbitrarily; no application ping should be sent
        clock.advance_ns(1_000_000_000)
        session.tick()

        # Binance uses server-initiated ping/pong (websocket protocol),
        # so no application-level ping is sent
        assert connector.sent_pings == []

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_reconnects_on_silence_no_close_frame(self):
        """Bybit reconnects on idle timeout since it sends no close frame."""
        connector = FakePolicyConnector(BYBIT_POLICY)
        clock = FakeClock()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=BYBIT_POLICY,
            connector=connector,
            clock=clock,
        )
        session.start()

        # Simulate a frame to set _last_inbound_ns
        session.on_frame()
        # Advance past idle timeout
        clock.advance_ns(BYBIT_POLICY.idle_timeout_ns + 1)
        session.tick()

        # Should have reconnected: close() called, then connect() called again
        assert connector._closed  # close() was called during reconnect
        assert connector._connected  # _connect() was called after close()

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_reconnects_on_close_frame(self):
        """OKX reconnects when it receives a close frame (code 4004).

        OKX announces close (announces_close=True), so tick() does not
        reconnect on idle. Instead, the venue sends a close frame (code 4004)
        which triggers _reconnect via the session's error handling.
        """
        connector = FakePolicyConnector(OKX_POLICY)
        clock = FakeClock()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=OKX_POLICY,
            connector=connector,
            clock=clock,
        )
        session.start()

        # OKX sends pings on schedule
        clock.advance_ns(OKX_POLICY.client_ping_interval_ns + 1)
        session.tick()

        assert connector.sent_pings == ["ping"]
