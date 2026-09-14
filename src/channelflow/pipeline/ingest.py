"""PRD §6.2's `ingest-binance`, as a process that can be run.

# @trace: REQ-WP-066

[[REQ-PIPE-001]] deferred this deliberately: "a live process attaching the same
sinks to a running connector is deployment work and adds nothing this cannot
already show." It was right about the second half and this is the first half --
the deployment work, now wanted, because a stack nobody can feed shows nothing.

**Everything that decides is already written and tested.** `StreamSession`
handles the connection's life, `normalize` turns a frame into a `TradeEvent`,
`BarBuilder` closes bars, `BarSink` commits them. This is the loop that turns
those into a process, and it is arranged so the untestable part -- a real socket
-- is the only part with no decisions in it.

**The loop's shape comes from a measurement.** Binance sends a protocol PING
every 20 seconds and drops a client that does not answer; `websockets` answers
from the connection's own task. So the socket lives in its own thread, and
everything here -- parsing, compressing, committing -- happens on the other side
of a queue where it cannot stop a pong.

**One step is one testable unit.** `step()` takes the frames that have arrived
and does everything with them; `run()` only decides when to call it. A daemon
whose behaviour lived in its loop could be tested only by running it.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.binance import normalize
from channelflow.connectors.session import StreamSession
from channelflow.pipeline.archive import FrameArchive

#: How often the bars buffered by the sink are committed. A commit per bar would
#: make the snapshot chain as long as the series (`BarSink` says why); a commit
#: per hour would lose an hour to a restart.
FLUSH_INTERVAL_NS = 60_000_000_000


class Drainable(Protocol):
    """A transport this loop can take frames from without blocking."""

    def drain(self) -> list[str]: ...


@dataclass(frozen=True)
class StepReport:
    """What one step did. Returned rather than logged, so a test can read it."""

    frames: int
    trades: int
    archived: str | None
    unparsed: int
    ignored: int
    flushed: str | None

    @property
    def did_nothing(self) -> bool:
        return self.frames == 0


@dataclass
class IngestDaemon:
    """One venue, one connection, one symbol's bars.

    Composition of several symbols is the caller's, the way `BarBuilder` says:
    one builder is one symbol and one timeframe, and a daemon that hid that
    would decide something the caller can see better.
    """

    session: StreamSession
    transport: Drainable
    archive: FrameArchive
    builder: BarBuilder
    venue: str
    market_type: str = "spot"
    #: Returns the wall clock in nanoseconds. Injected, so a test is not slow.
    now_ns: Callable[[], int] = field(default=lambda: time.time_ns())
    flush_bars: Callable[[], str | None] = field(default=lambda: None)

    #: Frames whose stream this daemon does not turn into events. Counted, not
    #: dropped silently: a subscription nobody consumes is a cost with no
    #: benefit, and it should be visible enough to remove.
    ignored: int = 0
    #: Frames that arrived and could not be read. Never fatal -- one bad frame
    #: must not end an ingest -- and never invisible.
    unparsed: int = 0
    _last_flush_ns: int = 0

    def start(self) -> None:
        self.session.start()
        self._last_flush_ns = self.now_ns()

    def step(self) -> StepReport:
        """Take what has arrived, archive it, and turn what is a trade into one."""
        frames = self.transport.drain()
        received_at = self.now_ns()
        archived = None
        trades = 0
        unparsed_before, ignored_before = self.unparsed, self.ignored

        for frame in frames:
            # The archive first, and unconditionally. A frame this build cannot
            # read is exactly the frame a later one will want (§7's
            # "re-normalization may be required"), so it is kept before anything
            # is decided about it.
            written = self.archive.add(received_at_ns=received_at, frame=frame)
            archived = written or archived
            self.session.on_frame()
            if self._consume(frame, received_at):
                trades += 1

        self.session.tick()

        flushed = None
        if received_at - self._last_flush_ns >= FLUSH_INTERVAL_NS:
            flushed = self.flush_bars()
            self.archive.flush()
            self._last_flush_ns = received_at

        return StepReport(
            frames=len(frames),
            trades=trades,
            archived=archived,
            unparsed=self.unparsed - unparsed_before,
            ignored=self.ignored - ignored_before,
            flushed=flushed,
        )

    def _consume(self, frame: str, received_at_ns: int) -> bool:
        try:
            envelope = json.loads(frame)
        except ValueError:
            self.unparsed += 1
            return False

        stream = envelope.get("stream")
        payload: Any = envelope.get("data")
        if not isinstance(stream, str) or not isinstance(payload, dict):
            self.unparsed += 1
            return False

        if not stream.endswith("@aggTrade"):
            # Depth and the rest are archived and not turned into events yet:
            # bars need trades, and a book this build does not maintain would be
            # a half-built one. They are counted so the gap is visible.
            self.ignored += 1
            return False

        try:
            trade = normalize.agg_trade(
                payload,
                venue=self.venue,
                market_type=self.market_type,
                ingest_time_ns=received_at_ns,
            )
        except Exception:  # noqa: BLE001 -- a bad frame is not a reason to stop
            self.unparsed += 1
            return False

        self.builder.add(trade)
        return True

    def run(self, *, steps: int | None = None, pause_seconds: float = 0.2) -> list[StepReport]:
        """Step until told to stop. `steps` bounds it, for a test and a backfill.

        The pause is what keeps this from spinning on an idle socket; the socket
        thread is not waiting on it.
        """
        self.start()
        reports = []
        taken = 0
        try:
            while steps is None or taken < steps:
                reports.append(self.step())
                taken += 1
                if pause_seconds:
                    time.sleep(pause_seconds)
        finally:
            self.stop()
        return reports

    def stop(self) -> StepReport | None:
        """Commit what is buffered and close the connection.

        Ordered: flush first, then close. Closing first would leave the last
        minute of frames and the last bars in memory, and a restart would look
        like a gap in the data rather than a gap in the shutdown.
        """
        flushed = self.flush_bars()
        archived = self.archive.flush()
        self.session.transport.close()
        return StepReport(
            frames=0, trades=0, archived=archived, unparsed=0, ignored=0, flushed=flushed
        )


def streams_for(symbols: Sequence[str]) -> tuple[str, ...]:
    """Binance's stream names for the symbols asked for.

    Lower case, because the venue's combined stream rejects anything else --
    measured, not read: an upper-case name connects and delivers nothing.
    """
    return tuple(f"{symbol.lower()}@aggTrade" for symbol in symbols)
