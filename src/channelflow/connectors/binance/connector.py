"""Binance connector using the existing WebsocketTransport.

# @trace: REQ-WP-076
"""

from __future__ import annotations

import queue
from collections.abc import Callable, Sequence

from channelflow.connectors.websocket import WebsocketTransport


class BinanceConnector:
    """Binance connector: uses WebsocketTransport with URL-based subscription."""

    def __init__(self, url_for: Callable[[Sequence[str]], str]) -> None:
        self._transport = WebsocketTransport(url_for=url_for)

    def connect(self, streams: Sequence[str]) -> None:
        self._transport.connect(streams)

    @property
    def frames(self) -> queue.Queue[str]:
        return self._transport.frames

    def send(self, payload: str) -> None:
        self._transport.send(payload)

    def pong(self) -> None:
        self._transport.pong()

    def close(self) -> None:
        self._transport.close()
