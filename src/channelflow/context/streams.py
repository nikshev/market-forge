"""A websocket stream inside the collector: frames to a handler, and a heartbeat only while
connected.

# @trace: REQ-WP-094
# @trace: REQ-WP-095

`StreamSession` already decides everything about a connection's life -- reconnect, backoff, pings,
the lifetime a venue closes at -- and is tested on a fake clock where it lives. What this adds is
what the collector needs on top, and nothing the session already does:

* **A frame the handler cannot read never stops the stream.** It is counted and the next one is
  handled. One malformed liquidation must not end a collection that is mostly well-formed.
* **A minute is covered only if the connection stayed up for the whole of it.** The heartbeat for
  the minute ending at `B` is written only if the session's current connection was made at or
  before `B - 1 minute` and the reader is alive at `B`. A reconnect inside a minute therefore
  uncovers that minute, which is what makes "no liquidations in this window" mean something.
* **A quiet stream is not reconnected for being quiet.** Liquidations are sparse -- minutes of
  silence are normal -- and a venue policy's silence limit (60 s on Binance) would drop and remake
  a healthy connection every minute. `stream_policy(quiet=True)` removes that limit for Binance,
  whose keepalive is the server's pings and so is invisible to the session. Bybit and OKX are
  pinged by the client and answer with a frame, which counts as inbound data, so they are never
  silent in practice and keep their policy unchanged: the limit that remains for them is "the
  venue stopped answering pings".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from channelflow.connectors.session import POLICIES, StreamSession, VenuePolicy

MINUTE_NS = 60_000_000_000


def stream_policy(venue: str, *, quiet: bool) -> VenuePolicy:
    try:
        policy = POLICIES[venue]
    except KeyError:
        raise ValueError(
            f"no stream policy for venue {venue!r}; known: {', '.join(sorted(POLICIES))}"
        ) from None
    return replace(policy, max_silence_ns=None) if quiet else policy


@dataclass
class StreamTask:
    session: StreamSession
    #: Called with each frame and the time it was received.
    handler: Callable[[str, int], None]
    #: Called with the minute-end a heartbeat covers.
    heartbeat: Callable[[int], None]
    now_ns: Callable[[], int]
    #: Called with a description of anything that failed, for the status counters.
    on_failure: Callable[[str], None]
    #: Called on every step with the time, so a stream that has gone quiet can still close its
    #: minutes (REQ-WP-095); `None` for a stream that has nothing to close.
    tick: Callable[[int], None] | None = None
    #: Called once for each new connection after the first: whatever was kept about the old one --
    #: a book, a flow baseline -- no longer describes the market (REQ-WP-095).
    on_reconnect: Callable[[], None] | None = None
    frames: int = 0
    _last_boundary_ns: int = 0
    _connected_at_ns: int = 0

    def start(self) -> None:
        self.session.start()
        self._last_boundary_ns = (self.now_ns() // MINUTE_NS) * MINUTE_NS
        self._connected_at_ns = self.session.connected_at_ns

    def step(self) -> None:
        received_at = self.now_ns()
        for frame in self.session.connector.drain_frames():
            self.frames += 1
            self.session.on_frame()
            try:
                self.handler(frame, received_at)
            except Exception as exc:  # noqa: BLE001 -- one bad frame is not a reason to stop
                self.on_failure(f"{type(exc).__name__}: {exc}")
        self.session.tick()
        if self.session.connected_at_ns != self._connected_at_ns:
            self._connected_at_ns = self.session.connected_at_ns
            if self.on_reconnect is not None:
                self.on_reconnect()
        now = self.now_ns()
        if self.tick is not None:
            self.tick(now)
        self._maybe_heartbeat(now)

    def _maybe_heartbeat(self, now: int) -> None:
        boundary = (now // MINUTE_NS) * MINUTE_NS
        if boundary <= self._last_boundary_ns:
            return
        self._last_boundary_ns = boundary
        connected_whole_minute = self.session.connected_at_ns <= boundary - MINUTE_NS
        if connected_whole_minute and self.session.connector.alive:
            self.heartbeat(boundary)
