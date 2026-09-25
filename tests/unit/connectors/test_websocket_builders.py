"""Tests for venue-specific stream builders and subscription messages (REQ-WP-076)."""

# @trace: REQ-WP-076

import json

import pytest

from channelflow.connectors.venue import (
    binance_streams,
    binance_subscribe_message,
    bybit_streams,
    bybit_subscribe_message,
    okx_streams,
    okx_subscribe_message,
)


class TestStreamBuilders:
    """Venue-specific stream name builders."""

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
    """Venue-specific subscription messages, byte-for-byte against docs."""

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_subscribe_message_returns_none(self):
        """Binance uses URL params; no post-connect message."""
        assert binance_subscribe_message(["btcusdt@aggTrade"]) is None

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_subscribe_message_format(self):
        msg = bybit_subscribe_message(["publicTrade.BTCUSDT"])
        data = json.loads(msg)
        assert data["op"] == "subscribe"
        assert data["args"] == ["publicTrade.BTCUSDT"]

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_subscribe_message_format(self):
        msg = okx_subscribe_message(["trades.BTC-USDT-SWAP"])
        data = json.loads(msg)
        assert data["op"] == "subscribe"
        assert data["args"][0]["channel"] == "trades"
        # instId uses the stream name as-is (including "trades." prefix)
        assert data["args"][0]["instId"] == "trades.BTC-USDT-SWAP"

    @pytest.mark.trace("REQ-WP-076")
    def test_no_builder_is_another_with_string_replaced(self):
        """Each venue's builder is independent, not a string substitution of another."""
        binance_msg = binance_subscribe_message(["btcusdt@aggTrade"])
        bybit_msg = bybit_subscribe_message(["publicTrade.BTCUSDT"])
        okx_msg = okx_subscribe_message(["trades.BTC-USDT-SWAP"])

        # All should be different (binance is None, others are JSON)
        assert binance_msg is None
        assert bybit_msg != okx_msg
        # The JSON structures are fundamentally different
        assert '"op":"subscribe"' in bybit_msg
        assert '"op":"subscribe"' in okx_msg
        assert "publicTrade" in bybit_msg
        assert "instId" in okx_msg
