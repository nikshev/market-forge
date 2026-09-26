"""Bybit V5 connector.

# @trace: REQ-WP-076

Bybit V5 subscribes by sending a JSON message after connecting:
{"op": "subscribe", "args": ["publicTrade.BTCUSDT", ...]}

Ping: {"op": "ping"} (client sends), pong is {"op": "pong"}.
No close frame on idle disconnect.
"""

from __future__ import annotations

import logging
import queue
import threading

from websockets.sync import client

logger = logging.getLogger(__name__)


class BybitConnector:
    """Bybit V5 connector: connects, sends subscribe message, reads frames."""

    def __init__(self, url: str, subscribe_msg: str) -> None:
        self._url = url
        self._subscribe_msg = subscribe_msg
        self._ws: client.ClientConnection | None = None
        self._frames: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stopping = False
        self._connected = False

    def connect(self, streams: tuple[str, ...]) -> None:

        def run() -> None:
            try:
                logger.info("Connecting to Bybit WebSocket at %s", self._url)
                with client.connect(self._url) as ws:
                    self._ws = ws
                    logger.info(
                        "Connected to Bybit WebSocket, sending subscribe message: %s",
                        self._subscribe_msg,
                    )
                    self._ws.send(self._subscribe_msg)
                    self._connected = True
                    logger.info("Starting frame receive loop")
                    while not self._stopping:
                        try:
                            logger.debug("Waiting for frame...")
                            frame = self._ws.recv()
                            logger.info("Received raw frame: %s", frame[:200] if frame else "None")
                            if isinstance(frame, bytes):
                                frame = frame.decode()
                            logger.info("Received frame: %s", frame[:200])
                            self._frames.put(frame)
                        except Exception as e:
                            logger.warning("Error receiving frame: %s", e)
                            break
            except Exception as e:
                logger.error("Bybit WebSocket connection error: %s", e)
            finally:
                self._connected = False
                logger.info("Bybit WebSocket connection closed")

        self._thread = threading.Thread(target=run, name="bybit-ws", daemon=True)
        self._thread.start()

    @property
    def frames(self) -> queue.Queue[str]:
        return self._frames

    def drain_frames(self) -> list[str]:
        out = []
        while True:
            try:
                out.append(self._frames.get_nowait())
            except queue.Empty:
                return out

    def send(self, payload: str) -> None:
        if self._ws:
            self._ws.send(payload)

    def pong(self) -> None:
        # Bybit expects client to send ping; server responds with pong
        pass

    def close(self) -> None:
        self._stopping = True
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)
