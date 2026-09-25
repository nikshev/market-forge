"""Tests for BinanceConnector.

# @trace: REQ-WP-076
"""

from unittest.mock import MagicMock, patch

import pytest

from channelflow.connectors.binance.connector import BinanceConnector


class TestBinanceConnector:
    @pytest.mark.trace("REQ-WP-076")
    def test_connect_calls_transport_with_correct_url(self):
        mock_transport = MagicMock()
        with patch(
            "channelflow.connectors.binance.connector.WebsocketTransport",
            return_value=mock_transport,
        ):
            connector = BinanceConnector(url_for=lambda streams: "wss://test/stream")
            connector.connect(("btcusdt@aggTrade",))
            mock_transport.connect.assert_called_once_with(("btcusdt@aggTrade",))

    @pytest.mark.trace("REQ-WP-076")
    def test_frames_delegates_to_transport(self):
        mock_transport = MagicMock()
        mock_frames = MagicMock()
        mock_transport.frames = mock_frames
        with patch(
            "channelflow.connectors.binance.connector.WebsocketTransport",
            return_value=mock_transport,
        ):
            connector = BinanceConnector(url_for=lambda streams: "wss://test/stream")
            assert connector.frames is mock_frames

    @pytest.mark.trace("REQ-WP-076")
    def test_send_delegates_to_transport(self):
        mock_transport = MagicMock()
        with patch(
            "channelflow.connectors.binance.connector.WebsocketTransport",
            return_value=mock_transport,
        ):
            connector = BinanceConnector(url_for=lambda streams: "wss://test/stream")
            connector.send("test payload")
            mock_transport.send.assert_called_once_with("test payload")

    @pytest.mark.trace("REQ-WP-076")
    def test_pong_delegates_to_transport(self):
        mock_transport = MagicMock()
        with patch(
            "channelflow.connectors.binance.connector.WebsocketTransport",
            return_value=mock_transport,
        ):
            connector = BinanceConnector(url_for=lambda streams: "wss://test/stream")
            connector.pong()
            mock_transport.pong.assert_called_once()

    @pytest.mark.trace("REQ-WP-076")
    def test_close_delegates_to_transport(self):
        mock_transport = MagicMock()
        with patch(
            "channelflow.connectors.binance.connector.WebsocketTransport",
            return_value=mock_transport,
        ):
            connector = BinanceConnector(url_for=lambda streams: "wss://test/stream")
            connector.close()
            mock_transport.close.assert_called_once()
