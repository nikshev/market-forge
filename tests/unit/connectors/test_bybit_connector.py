"""Tests for BybitConnector.

# @trace: REQ-WP-076
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from channelflow.connectors.bybit.connector import BybitConnector
from channelflow.connectors.venue import bybit_subscribe_message


class TestBybitConnector:
    def test_subscribe_message_format(self):
        msg = bybit_subscribe_message(["publicTrade.BTCUSDT"])
        data = json.loads(msg)
        assert data["op"] == "subscribe"
        assert data["args"] == ["publicTrade.BTCUSDT"]

    def test_connect_sends_subscribe_message(self):
        with patch("websockets.sync.client.connect") as mock_connect:
            mock_ws = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_ws
            
            connector = BybitConnector(
                url="wss://stream.bybit.com/v5/public/linear",
                subscribe_msg='{"op":"subscribe","args":["publicTrade.BTCUSDT"]}'
            )
            connector.connect(("publicTrade.BTCUSDT",))
            
            # Verify connect was called
            mock_connect.assert_called_once_with("wss://stream.bybit.com/v5/public/linear")
            # Verify subscribe message was sent
            mock_ws.send.assert_called_once()
            sent = mock_ws.send.call_args[0][0]
            data = json.loads(sent)
            assert data["op"] == "subscribe"
            assert "publicTrade.BTCUSDT" in data["args"]

    def test_frames_delegates_to_internal_queue(self):
        connector = BybitConnector(url="wss://test", subscribe_msg="{}")
        mock_queue = MagicMock()
        connector._frames = mock_queue
        assert connector.frames is mock_queue

    def test_send_delegates_to_ws(self):
        with patch("websockets.sync.client.connect"):
            connector = BybitConnector(url="wss://test", subscribe_msg="{}")
            connector._ws = MagicMock()
            connector.send("test payload")
            connector._ws.send.assert_called_once_with("test payload")

    def test_pong_noop(self):
        with patch("websockets.sync.client.connect"):
            connector = BybitConnector(url="wss://test", subscribe_msg="{}")
            # Should not raise
            connector.pong()

    def test_close_closes_ws(self):
        with patch("websockets.sync.client.connect") as mock_connect:
            mock_ws = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_ws
            
            connector = BybitConnector(url="wss://test", subscribe_msg="{}")
            connector.connect(("test",))
            connector.close()
            
            mock_ws.close.assert_called_once()