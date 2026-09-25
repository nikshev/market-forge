"""Tests for OkxConnector.

# @trace: REQ-WP-076
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from channelflow.connectors.okx.connector import OkxConnector
from channelflow.connectors.venue import okx_subscribe_message


class TestOkxConnector:
    @pytest.mark.trace("REQ-WP-076")
    def test_subscribe_message_format(self):
        msg = okx_subscribe_message(["trades.BTC-USDT-SWAP"])
        data = json.loads(msg)
        assert data["op"] == "subscribe"
        assert data["args"][0]["channel"] == "trades"
        assert data["args"][0]["instId"] == "trades.BTC-USDT-SWAP"

    @pytest.mark.trace("REQ-WP-076")
    def test_connect_sends_subscribe_message(self):
        with patch("websockets.sync.client.connect") as mock_connect:
            mock_ws = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_ws

            connector = OkxConnector(
                url="wss://ws.okx.com:8443/api/v5/market",
                subscribe_msg=json.dumps(
                    {"op": "subscribe", "args": [{"channel": "trades", "instId": "BTC-USDT-SWAP"}]}
                ),
            )
            connector.connect(("trades.BTC-USDT-SWAP",))

            mock_connect.assert_called_once_with("wss://ws.okx.com:8443/api/v5/market")
            mock_ws.send.assert_called_once()
            sent = mock_ws.send.call_args[0][0]
            data = json.loads(sent)
            assert data["op"] == "subscribe"
            assert data["args"][0]["channel"] == "trades"
            assert data["args"][0]["instId"] == "BTC-USDT-SWAP"

    @pytest.mark.trace("REQ-WP-076")
    def test_pong_sends_bare_ping(self):
        with patch("websockets.sync.client.connect"):
            connector = OkxConnector(url="wss://test", subscribe_msg="{}")
            connector._ws = MagicMock()
            connector.pong()
            connector._ws.send.assert_called_once_with("ping")

    @pytest.mark.trace("REQ-WP-076")
    def test_close_closes_ws(self):
        with patch("websockets.sync.client.connect") as mock_connect:
            mock_ws = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_ws

            connector = OkxConnector(url="wss://test", subscribe_msg="{}")
            connector.connect(("trades.BTC-USDT-SWAP",))
            connector.close()

            mock_ws.close.assert_called_once()
