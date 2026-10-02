"""Binance connector using the existing WebsocketTransport.

# @trace: REQ-WP-076
# @trace: REQ-WP-078
"""

from __future__ import annotations

import queue
from collections.abc import Callable, Sequence

from channelflow.connectors.websocket import WebsocketTransport


class BinanceConnector:
    """Binance connector: uses WebsocketTransport with URL-based subscription."""

    def __init__(self, url_for: Callable[[Sequence[str]], str]) -> None:
        self._transport = WebsocketTransport(url_for=url_for, name="binance")

    def connect(self, streams: Sequence[str]) -> None:
        self._transport.connect(streams)

    @property
    def alive(self) -> bool:
        return self._transport.alive

    @property
    def frames(self) -> queue.Queue[str]:
        return self._transport.frames

    def drain_frames(self) -> list[str]:
        return self._transport.drain()

    def send(self, payload: str) -> None:
        self._transport.send(payload)

    def pong(self) -> None:
        self._transport.pong()

    def close(self) -> None:
        self._transport.close()
