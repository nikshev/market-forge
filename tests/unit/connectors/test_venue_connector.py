"""Tests for the VenueConnector protocol and VenueConfig registry.

# @trace: REQ-WP-076
"""

import queue

from channelflow.connectors.venue import (
    BINANCE_POLICY,
    BYBIT_POLICY,
    OKX_POLICY,
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

    def pong(self):
        pass

    def close(self):
        self._closed = True

    @property
    def frames(self):
        return self._frames


class TestVenueConnectorProtocol:
    """Tests that the VenueConnector protocol is well-defined."""

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

    def test_registry_contains_three_venues(self):
        assert set(VENUE_REGISTRY.keys()) == {"binance", "bybit", "okx"}

    def test_each_venue_has_required_fields(self):
        for name, config in VENUE_REGISTRY.items():
            assert hasattr(config, "connector")
            assert hasattr(config, "stream_builder")
            assert hasattr(config, "policy")
            assert hasattr(config, "archive_prefix")
            assert config.archive_prefix == name

    def test_binance_config(self):
        config = VENUE_REGISTRY["binance"]
        assert config.connector.endswith("BinanceConnector")
        assert config.stream_builder is binance_streams
        assert config.policy.venue == "binance"
        assert config.archive_prefix == "binance"

    def test_bybit_config(self):
        config = VENUE_REGISTRY["bybit"]
        assert config.connector.endswith("BybitConnector")
        assert config.stream_builder is bybit_streams
        assert config.policy.venue == "bybit"
        assert config.archive_prefix == "bybit"

    def test_okx_config(self):
        config = VENUE_REGISTRY["okx"]
        assert config.connector.endswith("OkxConnector")
        assert config.stream_builder is okx_streams
        assert config.policy.venue == "okx"
        assert config.archive_prefix == "okx"


class TestStreamBuilders:
    """Tests for venue-specific stream name builders."""

    def test_binance_streams(self):
        streams = binance_streams(["BTCUSDT", "ETHUSDT"])
        assert streams == ("btcusdt@aggTrade", "ethusdt@aggTrade")

    def test_bybit_streams(self):
        streams = bybit_streams(["BTCUSDT", "ETHUSDT"])
        assert streams == ("publicTrade.BTCUSDT", "publicTrade.ETHUSDT")

    def test_okx_streams(self):
        streams = okx_streams(["BTC-USDT-SWAP", "ETH-USDT-SWAP"])
        assert streams == ("trades.BTC-USDT-SWAP", "trades.ETH-USDT-SWAP")

    def test_stream_builders_return_tuples(self):
        for builder in (binance_streams, bybit_streams, okx_streams):
            result = builder(["BTCUSDT"])
            assert isinstance(result, tuple)
            assert len(result) == 1


class TestSubscribeMessages:
    """Tests for venue-specific subscription messages."""

    def test_binance_subscribe_message_returns_none(self):
        """Binance uses URL params; no post-connect message."""
        assert binance_subscribe_message(["btcusdt@aggTrade"]) is None

    def test_bybit_subscribe_message_format(self):
        msg = bybit_subscribe_message(["publicTrade.BTCUSDT"])
        assert '"op":"subscribe"' in msg
        assert '"args"' in msg
        assert "publicTrade.BTCUSDT" in msg

    def test_okx_subscribe_message_format(self):
        msg = okx_subscribe_message(["trades.BTC-USDT-SWAP"])
        assert '"op":"subscribe"' in msg
        assert '"args"' in msg
        assert "trades" in msg
        assert "instId" in msg


class TestVenuePolicies:
    """Tests for venue-specific connection policies."""

    def test_binance_policy(self):
        p = BINANCE_POLICY
        assert p.venue == "binance"
        assert p.idle_timeout_ns == 24 * 60 * 60 * 1_000_000_000

    def test_bybit_policy(self):
        p = BYBIT_POLICY
        assert p.venue == "bybit"
        assert p.idle_timeout_ns == 60_700_000_000
        assert p.ping_payload == '{"op":"ping"}'
        assert p.announces_close is False

    def test_okx_policy(self):
        p = OKX_POLICY
        assert p.venue == "okx"
        assert p.idle_timeout_ns == 30_900_000_000
        assert p.ping_payload == "ping"
        assert p.announces_close is True

    def test_all_policies_have_min_connect_interval(self):
        for p in (BINANCE_POLICY, BYBIT_POLICY, OKX_POLICY):
            assert p.min_connect_interval_ns == 1_000_000_000


class TestUnknownVenue:
    def test_unknown_venue_not_in_registry(self):
        assert "unknown" not in VENUE_REGISTRY
        assert "hyperliquid" not in VENUE_REGISTRY
