"""The reader shared by venues that subscribe with a message after connecting.

# @trace: REQ-WP-078

Bybit and OKX each had a copy of this: open the socket, send the subscription, read frames
into a queue on a thread. The copies disagreed about what happens when it goes wrong --
Bybit logged an error, OKX swallowed it -- and neither could be asked whether the thread
was still running. That is how an OKX daemon opened a URL that answers `HTTP 404`, lost
the exception, and reported nothing for six days.

**A reader never ends without a log line saying why.** A failed open, a failure mid-stream
and a close from the venue each log at WARNING with the venue and the cause; a close this
process asked for logs at INFO. `alive` is the fact the session polls; the cause is logged
here, where the exception is in hand.

**Each connection has its own stop signal.** A shared flag, reset by the next `connect()`,
would let a reader that had not finished stopping read on beside its replacement and put
every frame in the queue twice.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any

from websockets.sync import client

from channelflow.connectors.venue import rejection

logger = logging.getLogger(__name__)

#: How long `close` waits for the reader to finish.
CLOSE_JOIN_SECONDS = 5.0


class SubscribingConnector:
    """Connects, sends one subscription, and reads frames until told to stop or it fails."""

    #: The venue's name, for the log and for `rejection`. Set by each subclass.
    venue = "unknown"

    def __init__(self, url: str, subscribe_msg: str) -> None:
        self._url = url
        self._subscribe_msg = subscribe_msg
        self._ws: Any = None
        self._frames: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._connected = False

    def connect(self, streams: tuple[str, ...]) -> None:
        stop = threading.Event()
        self._stop = stop
        venue = self.venue

        def run() -> None:
            opened = False
            try:
                logger.info("%s: connecting to %s", venue, self._url)
                with client.connect(self._url) as ws:
                    opened = True
                    self._ws = ws
                    ws.send(self._subscribe_msg)
                    self._connected = True
                    logger.info("%s: connected, subscription sent", venue)
                    while not stop.is_set():
                        frame = ws.recv()
                        if isinstance(frame, bytes):
                            frame = frame.decode()
                        refusal = rejection(venue, frame)
                        if refusal is not None:
                            logger.warning("%s rejected the request: %s", venue, refusal)
                        # Queued whether or not it was a refusal: the archive keeps what
                        # the venue said.
                        self._frames.put(frame)
            except Exception as error:
                if stop.is_set():
                    logger.info("%s: reader stopped", venue)
                elif opened:
                    logger.warning("%s: reader ended: %s: %s", venue, type(error).__name__, error)
                else:
                    logger.warning(
                        "%s: could not open %s: %s: %s",
                        venue,
                        self._url,
                        type(error).__name__,
                        error,
                    )
            finally:
                self._connected = False

        self._thread = threading.Thread(target=run, name=f"{venue}-ws", daemon=True)
        self._thread.start()

    @property
    def alive(self) -> bool:
        """The reader is running: started by `connect`, not yet returned, not stopped."""
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop.is_set()

    @property
    def frames(self) -> queue.Queue[str]:
        return self._frames

    def drain_frames(self) -> list[str]:
        out: list[str] = []
        while True:
            try:
                out.append(self._frames.get_nowait())
            except queue.Empty:
                return out

    def send(self, payload: str) -> None:
        if self._ws:
            self._ws.send(payload)

    def pong(self) -> None:  # pragma: no cover -- each venue decides
        raise NotImplementedError

    def close(self) -> None:
        self._stop.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:  # noqa: BLE001 -- closing a socket that is already gone
                pass
        if self._thread:
            self._thread.join(timeout=CLOSE_JOIN_SECONDS)
