"""The live edge: a real socket behind [[REQ-WP-051]]'s `Transport` protocol.

# @trace: REQ-WP-066
# @trace: REQ-WP-078

`StreamSession` already decides everything about a connection's life -- when to
reconnect, when a silence means the venue gave up, when to ping -- and is tested
against a `FakeClock` and a fake transport. What was missing was the edge. This
is it, and it is deliberately thin: the part that cannot be tested against a
recording should be the part with no decisions in it.

**The socket runs in its own thread, doing nothing but I/O.** Measured on
2026-09-13: Binance sends a protocol PING every 20 seconds (intervals 20.0,
20.1, 19.9, 20.1... over 400 seconds) and disconnects a client that does not
answer. `websockets` answers automatically -- but from the connection's own
task, which only runs while its event loop does. Normalising a frame, gzipping
an archive object or committing to Iceberg on that loop would stop the pongs and
the venue would drop us, with no error and no close frame to explain it.

So frames cross into the consumer through a queue, and everything expensive
happens on the other side of it.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

#: How long `close` waits for the socket thread to finish before giving up on
#: it. Long enough for a clean websocket close, short enough that a wedged
#: thread does not hold a restart.
CLOSE_TIMEOUT_SECONDS = 5.0

#: How long a read waits before returning nothing, so the consumer can run its
#: own timers -- `StreamSession.tick`, an archive flush -- instead of blocking
#: until the venue speaks.
POLL_SECONDS = 0.2


class NotConnected(RuntimeError):
    """A send or a read was attempted before `connect`, or after `close`."""


@dataclass
class WebsocketTransport:
    """One websocket connection, owned by one thread.

    `url_for` builds the venue's URL from the streams asked for, so this class
    knows nothing about any venue's query-string convention.
    """

    url_for: Callable[[Sequence[str]], str]
    #: Injected so a test can supply a connector that never touches a network.
    connect_to: Callable[..., Any] | None = None
    #: The venue this transport serves, for the log. The transport knows no venue's
    #: conventions, but a line saying "the websocket reader ended" is no use to someone
    #: reading five services' logs.
    name: str = "websocket"

    #: Frames as the venue sent them, in arrival order.
    frames: queue.Queue[str] = field(default_factory=queue.Queue)
    #: The deepest the queue has been. A consumer that cannot keep up shows up
    #: here rather than as memory growth nobody attributes.
    high_water: int = 0

    _thread: threading.Thread | None = None
    _loop: asyncio.AbstractEventLoop | None = None
    _socket: Any = None
    _ready: threading.Event = field(default_factory=threading.Event)
    _stopping: threading.Event = field(default_factory=threading.Event)
    _failure: BaseException | None = None

    def connect(self, streams: Sequence[str]) -> None:
        url = self.url_for(streams)
        self._stopping.clear()
        self._ready.clear()
        self._failure = None
        self._thread = threading.Thread(
            target=self._run, args=(url,), name="websocket", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=CLOSE_TIMEOUT_SECONDS):
            raise NotConnected(f"the socket did not open within {CLOSE_TIMEOUT_SECONDS}s")
        if self._failure is not None:
            raise NotConnected(f"the socket failed to open: {self._failure}")

    def _run(self, url: str) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._pump(url))
        except BaseException as cause:  # noqa: BLE001 -- reported to the caller's thread
            self._failure = cause
            self._ready.set()
            # Also logged, here, where it is in hand. `_failure` is read only by `connect()`,
            # on the first connection; a failure afterwards used to end the thread in
            # silence, and a daemon whose socket died stayed `Up` for four days.
            if not self._stopping.is_set():
                logger.warning("%s: reader ended: %s: %s", self.name, type(cause).__name__, cause)
        finally:
            loop.close()

    async def _pump(self, url: str) -> None:
        connector = self.connect_to
        if connector is None:  # pragma: no cover -- the network path
            import websockets

            connector = websockets.connect
        # `ping_interval=None`: this client does not keep the connection alive
        # by pinging. Binance pings us, and the library answers; adding our own
        # would be traffic the venue never asked for.
        async with connector(url, ping_interval=None) as socket:
            self._socket = socket
            self._ready.set()
            while not self._stopping.is_set():
                try:
                    frame = await asyncio.wait_for(socket.recv(), timeout=POLL_SECONDS)
                except TimeoutError:
                    continue
                self.frames.put(frame if isinstance(frame, str) else frame.decode())
                self.high_water = max(self.high_water, self.frames.qsize())

    def send(self, payload: str) -> None:
        socket, loop = self._socket, self._loop
        if socket is None or loop is None:
            raise NotConnected("send before connect")
        asyncio.run_coroutine_threadsafe(socket.send(payload), loop).result(
            timeout=CLOSE_TIMEOUT_SECONDS
        )

    def pong(self) -> None:
        """Deliberately nothing.

        `websockets` answers a PING from the connection's own task, which is why
        that task must never be blocked. An explicit pong from here would be a
        second answer to one ping. `StreamSession` calls this on the venues whose
        policy is client-initiated; Binance's is not, and the measurement says
        the library's answer is the one that reaches the venue.
        """

    @property
    def alive(self) -> bool:
        """The reader thread is running and neither failed nor was told to stop."""
        thread = self._thread
        return (
            thread is not None
            and thread.is_alive()
            and self._failure is None
            and not self._stopping.is_set()
        )

    def close(self) -> None:
        self._stopping.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=CLOSE_TIMEOUT_SECONDS)
        self._thread = None
        self._socket = None
        self._loop = None

    def drain(self) -> list[str]:
        """Everything that has arrived, without waiting for more."""
        out = []
        while True:
            try:
                out.append(self.frames.get_nowait())
            except queue.Empty:
                return out


@dataclass
class ReplayTransport:
    """The same seam, fed from recorded frames.

    Not a test double: this is how CI and a backfill run the same daemon over
    what a live one archived ([[ADR-002]]'s line between a double and a second
    production path). Nothing downstream can tell which transport it is behind.
    """

    recorded: Iterable[str]
    _pending: list[str] = field(default_factory=list)
    connects: int = 0
    closed: bool = False

    def connect(self, streams: Sequence[str]) -> None:
        self.connects += 1
        self.closed = False
        self._pending = list(self.recorded)

    def send(self, payload: str) -> None:
        """A recording cannot be subscribed to or pinged, and saying so is
        better than pretending the venue answered."""

    def pong(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True
        self._pending.clear()

    def drain(self) -> list[str]:
        out, self._pending = self._pending, []
        return out


def binance_stream_url(streams: Sequence[str]) -> str:
    """Binance's combined stream, as measured rather than as documented.

    One connection carries every stream; the frame names which one it came from,
    which is what lets the archive stay uninterpreted.
    """
    return "wss://stream.binance.com:9443/stream?streams=" + "/".join(streams)
