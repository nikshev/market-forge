"""Bybit V5 connector.

# @trace: REQ-WP-076
# @trace: REQ-WP-078

Bybit V5 subscribes by sending a JSON message after connecting:
{"op": "subscribe", "args": ["publicTrade.BTCUSDT", ...]}

Ping: {"op": "ping"} (client sends), pong is {"op": "pong"}.
No close frame on idle disconnect.

The reader is `SubscribingConnector`'s, shared with OKX.
"""

from __future__ import annotations

from channelflow.connectors.subscribing import SubscribingConnector


class BybitConnector(SubscribingConnector):
    """Bybit V5 connector: connects, sends the subscribe message, reads frames."""

    venue = "bybit"

    def pong(self) -> None:
        """Bybit's pong is sent by the venue in answer to our ping; nothing to do."""
