"""Tests for the VenueConnector protocol and VenueConfig registry.

# @trace: REQ-WP-076
# @trace: REQ-WP-078
"""

import queue

import pytest

from channelflow.connectors.session import BINANCE, BYBIT, OKX, SECOND_NS
from channelflow.connectors.venue import (
    VENUE_REGISTRY,
    binance_streams,
    binance_subscribe_message,
    bybit_streams,
    bybit_subscribe_message,
    okx_streams,
    okx_subscribe_message,
)


class FakeConnector:
    """Minimal fake implementation of VenueConnector for testing."""

    def __init__(self):
        self._frames = queue.Queue()
        self._connected = False
        self._closed = False
        self.sent = []
        self.connected_streams = None

    def connect(self, streams):
        self._connected = True
        self.connected_streams = streams

    def send(self, payload):
        self.sent.append(payload)

    @property
    def alive(self) -> bool:
        """A fake whose reader never ends. `kill()` lives in `pipeline/fakes.py`."""
        return True

    def pong(self):
        pass

    def close(self):
        self._closed = True

    @property
    def frames(self):
        return self._frames


class TestVenueConnectorProtocol:
    """Tests that the VenueConnector protocol is well-defined."""

    @pytest.mark.trace("REQ-WP-076")
    def test_protocol_has_required_methods(self):
        """VenueConnector defines the required interface."""
        # The protocol itself is an abstract definition; we test that a
        # concrete implementation satisfies it.
        fake = FakeConnector()
        assert hasattr(fake, "connect")
        assert hasattr(fake, "send")
        assert hasattr(fake, "pong")
        assert hasattr(fake, "close")
        assert hasattr(fake, "frames")

    @pytest.mark.trace("REQ-WP-076")
    def test_fake_implementation_satisfies_protocol(self):
        """A minimal fake implementation satisfies the protocol."""
        fake = FakeConnector()
        fake.connect(["test"])
        fake.send("test")
        fake.pong()
        fake.close()
        assert fake._connected
        assert fake.sent == ["test"]
        assert fake._closed


class TestVenueRegistry:
    """Tests for the venue configuration registry."""

    @pytest.mark.trace("REQ-WP-076")
    def test_registry_contains_three_venues(self):
        assert set(VENUE_REGISTRY.keys()) == {"binance", "bybit", "okx"}

    @pytest.mark.trace("REQ-WP-076")
    def test_each_venue_has_required_fields(self):
        for name, config in VENUE_REGISTRY.items():
            assert hasattr(config, "connector")
            assert hasattr(config, "stream_builder")
            assert hasattr(config, "policy")
            assert hasattr(config, "url")
            assert hasattr(config, "subscribe_message")
            # The venue is added to an archive key once, by `FrameArchive.key_for`. A prefix
            # held here was prepended by `build_daemon` as well and filed every frame at the
            # bucket root.
            assert not hasattr(config, "archive_prefix"), name

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_config(self):
        config = VENUE_REGISTRY["binance"]
        assert config.connector.endswith("BinanceConnector")
        assert config.stream_builder is binance_streams
        assert config.policy.venue == "binance"
        assert config.url is None, "Binance subscribes through its URL"
        assert config.subscribe_message(["BTCUSDT"]) is None

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_config(self):
        config = VENUE_REGISTRY["bybit"]
        assert config.connector.endswith("BybitConnector")
        assert config.stream_builder is bybit_streams
        assert config.policy.venue == "bybit"
        assert config.url == "wss://stream.bybit.com/v5/public/linear"
        assert '"publicTrade.BTCUSDT"' in config.subscribe_message(["BTCUSDT"])

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_config(self):
        config = VENUE_REGISTRY["okx"]
        assert config.connector.endswith("OkxConnector")
        assert config.stream_builder is okx_streams
        assert config.policy.venue == "okx"
        assert config.url == "wss://ws.okx.com:8443/ws/v5/public"
        message = config.subscribe_message(["BTC-USDT-SWAP"])
        assert '"instId": "BTC-USDT-SWAP"' in message
        assert "trades.BTC-USDT-SWAP" not in message, "a stream label is not an instrument"


class TestStreamBuilders:
    """Tests for venue-specific stream name builders."""

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_streams(self):
        streams = binance_streams(["BTCUSDT", "ETHUSDT"])
        assert streams == ("btcusdt@aggTrade", "ethusdt@aggTrade")

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_streams(self):
        streams = bybit_streams(["BTCUSDT", "ETHUSDT"])
        assert streams == ("publicTrade.BTCUSDT", "publicTrade.ETHUSDT")

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_streams(self):
        streams = okx_streams(["BTC-USDT-SWAP", "ETH-USDT-SWAP"])
        assert streams == ("trades.BTC-USDT-SWAP", "trades.ETH-USDT-SWAP")

    @pytest.mark.trace("REQ-WP-076")
    def test_stream_builders_return_tuples(self):
        for builder in (binance_streams, bybit_streams, okx_streams):
            result = builder(["BTCUSDT"])
            assert isinstance(result, tuple)
            assert len(result) == 1


class TestSubscribeMessages:
    """Tests for venue-specific subscription messages."""

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_subscribe_message_returns_none(self):
        """Binance uses URL params; no post-connect message."""
        assert binance_subscribe_message(["btcusdt@aggTrade"]) is None

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_subscribe_message_format(self):
        msg = bybit_subscribe_message(["publicTrade.BTCUSDT"])
        assert '"op":"subscribe"' in msg
        assert '"args"' in msg
        assert "publicTrade.BTCUSDT" in msg

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_subscribe_message_format(self):
        msg = okx_subscribe_message(["trades.BTC-USDT-SWAP"])
        assert '"op":"subscribe"' in msg
        assert '"args"' in msg
        assert "trades" in msg
        assert "instId" in msg


class TestVenuePolicies:
    """Tests for venue-specific connection policies."""

    @pytest.mark.trace("REQ-WP-076")
    @pytest.mark.trace("REQ-WP-078")
    def test_binance_policy(self):
        """A 24-hour stream *lifetime*, not a 24-hour idle timeout.

        This test asserted `idle_timeout_ns == 24 hours` and was green, which is how the
        daemon's silence threshold came to be 48 hours with nothing noticing.
        """
        p = VENUE_REGISTRY["binance"].policy
        assert p is BINANCE
        assert p.venue == "binance"
        assert p.stream_lifetime_ns == 24 * 60 * 60 * SECOND_NS
        assert p.idle_timeout_ns is None

    @pytest.mark.trace("REQ-WP-076")
    @pytest.mark.trace("REQ-WP-078")
    def test_bybit_policy(self):
        p = VENUE_REGISTRY["bybit"].policy
        assert p is BYBIT
        assert p.venue == "bybit"
        assert p.idle_timeout_ns == 60 * SECOND_NS
        assert p.ping_payload == '{"op":"ping"}'
        assert p.announces_close is False

    @pytest.mark.trace("REQ-WP-076")
    @pytest.mark.trace("REQ-WP-078")
    def test_okx_policy(self):
        p = VENUE_REGISTRY["okx"].policy
        assert p is OKX
        assert p.venue == "okx"
        assert p.idle_timeout_ns == 30 * SECOND_NS
        assert p.ping_payload == "ping"
        assert p.announces_close is True

    @pytest.mark.trace("REQ-WP-076")
    def test_all_policies_have_min_connect_interval(self):
        for p in (BINANCE, BYBIT, OKX):
            assert p.min_connect_interval_ns == 1_000_000_000


class TestUnknownVenue:
    @pytest.mark.trace("REQ-WP-076")
    def test_unknown_venue_not_in_registry(self):
        assert "unknown" not in VENUE_REGISTRY
        assert "hyperliquid" not in VENUE_REGISTRY
