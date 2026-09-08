"""Stream lifecycle: keepalive, reconnection, and counting what went wrong.

# @trace: REQ-WP-003

The transport and the clock are arguments, not imports. That is what lets the
whole lifecycle be tested without opening a socket (FR-018) -- PRD section 35.6
lists reconnect among the things connector tests must cover, and a test that
needs a live venue to prove reconnection would never run in the fast gate.

Binance closes a stream after 24 hours. Reconnecting *after* that means losing
whatever arrived in the gap, so the session moves first. And a reconnected
stream cannot resume its book: no update that arrived during the gap can be
recovered, so PRD section 11.1's procedure starts again from a snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

#: Binance closes a websocket stream 24 hours after it opens.
STREAM_LIFETIME_NS = 24 * 60 * 60 * 1_000_000_000


class Transport(Protocol):
    """What the session needs from a connection. Deliberately four methods."""

    def connect(self, streams: tuple[str, ...]) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...


class Clock(Protocol):
    def now_ns(self) -> int: ...


class FakeClock:
    """A clock the tests drive. Lives here so the lifetime arithmetic is
    exercised by the same code path in tests and in production."""

    def __init__(self, start_ns: int = 0) -> None:
        self._now = start_ns

    def now_ns(self) -> int:
        return self._now

    def advance_ns(self, delta: int) -> None:
        self._now += delta


@dataclass
class ConnectorMetrics:
    """FR-017. A connector that fails silently is indistinguishable from an
    idle one, and the difference matters at three in the morning."""

    connection_failures: int = 0
    sequence_gaps: int = 0
    normalization_failures: int = 0
    poll_failures: int = 0


@dataclass
class StreamSession:
    """One websocket subscription and its lifecycle."""

    streams: tuple[str, ...]
    transport: Transport
    clock: Clock
    metrics: ConnectorMetrics = field(default_factory=ConnectorMetrics)

    _connected_at_ns: int = 0
    _needs_snapshot: bool = True

    @property
    def needs_snapshot(self) -> bool:
        """True until a snapshot is taken, and true again after any reconnect."""
        return self._needs_snapshot

    def snapshot_taken(self) -> None:
        self._needs_snapshot = False

    def start(self) -> None:
        self._connect()

    def _connect(self) -> None:
        try:
            self.transport.connect(self.streams)
        except Exception:
            self.metrics.connection_failures += 1
            raise
        self._connected_at_ns = self.clock.now_ns()
        # Any new connection means the book must be rebuilt: updates that
        # arrived while disconnected cannot be recovered.
        self._needs_snapshot = True

    def tick(self) -> None:
        """Advance the lifecycle. Called on a timer by the ingestion loop."""
        age = self.clock.now_ns() - self._connected_at_ns
        if age >= STREAM_LIFETIME_NS:
            self.transport.close()
            self._connect()

    def on_ping(self) -> None:
        """FR-013. Binance disconnects a client that does not answer."""
        self.transport.pong()

    def record_sequence_gap(self) -> None:
        self.metrics.sequence_gaps += 1

    def record_normalization_failure(self) -> None:
        self.metrics.normalization_failures += 1

    def record_poll_failure(self) -> None:
        self.metrics.poll_failures += 1
