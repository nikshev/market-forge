"""OKX v5 connector.

# @trace: REQ-WP-076

OKX v5 subscribes by sending a JSON message after connecting:
{"op": "subscribe", "args": [{"channel": "trades", "instId": "BTC-USDT-SWAP"}]}

Ping: "ping" (bare string), pong is "pong" (bare string).
Idle timeout ~30s, closes with code 4004.
"""

from __future__ import annotations

import queue
import threading

from websockets.sync import client


class OkxConnector:
    """OKX v5 connector: connects, sends subscribe message, reads frames."""

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
                with client.connect(self._url) as ws:
                    self._ws = ws
                    self._ws.send(self._subscribe_msg)
                    self._connected = True
                    while not self._stopping:
                        try:
                            frame = self._ws.recv()
                            if isinstance(frame, bytes):
                                frame = frame.decode()
                            self._frames.put(frame)
                        except Exception:
                            break
            finally:
                self._connected = False

        self._thread = threading.Thread(target=run, name="okx-ws", daemon=True)
        self._thread.start()

    @property
    def frames(self) -> queue.Queue[str]:
        return self._frames

    def send(self, payload: str) -> None:
        if self._ws:
            self._ws.send(payload)

    def pong(self) -> None:
        # OKX expects bare "ping", responds with "pong"
        if self._ws:
            self._ws.send("ping")

    def close(self) -> None:
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        # Note: thread will exit on its own when _stopping is set
