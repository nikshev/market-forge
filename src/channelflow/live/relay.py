"""The API's side of the live feed: a cache, and the loop that fills it (REQ-WP-102).

# @trace: REQ-WP-102

**The cache is the last thirty minutes of each series' 1m bars**, which is more than the stretch
the table can be behind (the ingest commits fifteen bars at a time), so a page that opens gets the
gap in its first message. It is rebuilt on every start by reading the topic, whose retention is the
same thirty minutes -- a view that needs no table of its own.

**A final bar is never replaced.** Not by a forming bar however late it was ingested, and not by a
second final bar: a bar that is published is not amended (ADR-005), and a view that showed an
amendment would be repainting. Between forming bars the later ingest time wins.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from channelflow.live.messages import LiveBar, parse_record
from channelflow.transport import EventConsumer

logger = logging.getLogger(__name__)

MINUTE_NS = 60_000_000_000
WINDOW_NS = 30 * MINUTE_NS


@dataclass(frozen=True)
class _Held:
    bar: LiveBar
    ingest_time_ns: int


class LiveCache:
    def __init__(self, *, window_ns: int = WINDOW_NS) -> None:
        self._window_ns = window_ns
        self._series: dict[tuple[str, str], dict[int, _Held]] = defaultdict(dict)
        self._lock = threading.Lock()

    def apply(self, bar: LiveBar, *, ingest_time_ns: int) -> LiveBar | None:
        """Keep the bar if it is news; return it if so, `None` if it changed nothing."""
        opened = int(bar.open_time_ns)
        with self._lock:
            held = self._series[(bar.venue, bar.symbol)]
            current = held.get(opened)
            if current is not None:
                if current.bar.is_final:
                    return None
                if not bar.is_final and ingest_time_ns <= current.ingest_time_ns:
                    return None
            held[opened] = _Held(bar, ingest_time_ns)
            newest = max(held)
            for stale in [start for start in held if start < newest - self._window_ns]:
                del held[stale]
            return bar

    def snapshot(self, venue: str, symbol: str) -> list[LiveBar]:
        with self._lock:
            held = self._series.get((venue, symbol), {})
            return [held[start].bar for start in sorted(held)]


class LiveRelay:
    def __init__(
        self,
        consumer: EventConsumer,
        cache: LiveCache,
        forward: Callable[[LiveBar], None],
    ) -> None:
        self._consumer = consumer
        self.cache = cache
        self._forward = forward
        #: Records that were not live bars. Counted, said once, and skipped: one bad record must
        #: not stop the feed behind it.
        self.unreadable = 0

    def run_once(self, *, limit: int = 500, timeout: float | None = None) -> int:
        records = self._consumer.poll(limit=limit, timeout=0.0 if timeout is None else timeout)
        for record in records:
            try:
                bar = parse_record(record)
            except ValueError as exc:
                self.unreadable += 1
                if self.unreadable == 1:
                    logger.warning("live feed: unreadable record skipped: %s", exc)
                continue
            news = self.cache.apply(bar, ingest_time_ns=record.ingest_time_ns)
            if news is not None:
                self._forward(news)
        return len(records)

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                self.run_once(timeout=1.0)
            except Exception:  # noqa: BLE001 -- a broker that is down is retried, not fatal
                logger.exception("live feed: poll failed; retrying")
                stop.wait(2.0)
