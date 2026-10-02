"""OKX v5 connector.

# @trace: REQ-WP-076
# @trace: REQ-WP-078

OKX v5 subscribes by sending a JSON message after connecting:
{"op": "subscribe", "args": [{"channel": "trades", "instId": "BTC-USDT-SWAP"}]}

Ping: "ping" (bare string), pong is "pong" (bare string).
Idle timeout ~30s, closes with code 4004.

The reader is `SubscribingConnector`'s, shared with Bybit.
"""

from __future__ import annotations

from channelflow.connectors.subscribing import SubscribingConnector


class OkxConnector(SubscribingConnector):
    """OKX v5 connector: connects, sends the subscribe message, reads frames."""

    venue = "okx"

    def pong(self) -> None:
        # OKX expects the bare string "ping", and answers with "pong".
        if self._ws:
            self._ws.send("ping")
