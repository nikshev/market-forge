"""A connector whose reader can die without saying so (REQ-WP-078).

# @trace: REQ-WP-078

The existing fakes in this directory model a connector that works. The failure that
cost a feed for four days is the one they cannot express: the reader thread ends --
an exception, a close the connector does not turn into anything -- and the connector
still answers `connect`, `send` and `close` as if nothing had happened.

`kill()` is that. It changes `alive` and nothing else, so a session that does not ask
`alive` cannot tell, which is the point.
"""

from __future__ import annotations

import queue


class ControllableConnector:
    """A `VenueConnector` that records attempts and can be killed or made to refuse."""

    def __init__(self) -> None:
        self.attempts: list[int] = []
        self.connects: list[tuple[str, ...]] = []
        self.sent: list[str] = []
        self.closed = 0
        self.pongs = 0
        #: How many of the next `connect()` calls raise, as Binance's does when the
        #: socket does not open.
        self.refuse_next = 0
        #: When true, `connect()` returns and the reader is already dead -- Bybit's and
        #: OKX's normal failure shape, since their `connect()` only starts a thread.
        self.die_after_connect = False
        #: Stamped by the test with the clock's value so attempts can be timed.
        self.now_ns = lambda: 0
        self._alive = False
        self._frames: queue.Queue[str] = queue.Queue()

    # -- the VenueConnector surface ------------------------------------------

    def connect(self, streams: tuple[str, ...]) -> None:
        self.attempts.append(self.now_ns())
        if self.refuse_next > 0:
            self.refuse_next -= 1
            raise ConnectionError("refused")
        self.connects.append(tuple(streams))
        self._alive = not self.die_after_connect

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def pong(self) -> None:
        self.pongs += 1

    def close(self) -> None:
        self.closed += 1
        self._alive = False

    @property
    def alive(self) -> bool:
        return self._alive

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

    # -- the test's levers ---------------------------------------------------

    def kill(self) -> None:
        """The reader ends. No close frame, no exception reaches the session."""
        self._alive = False

    def push(self, frame: str) -> None:
        self._frames.put(frame)
