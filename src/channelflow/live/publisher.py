"""The ingest's side of the live feed (REQ-WP-102).

# @trace: REQ-WP-102
# @trace: REQ-WP-108

**Best effort, by design.** The bars table is the record; this is a view of it a few minutes
ahead. A broker that is down, slow or full is counted and the ingest carries on -- the one thing
this must never do is cost the ingest a trade.

**Forming bars at most four times a second per series**, because a busy market trades dozens of
times a second and the chart cannot draw them; **final bars always**, because the last forming
bar of a minute is not the bar (trades arrive for a few seconds after the minute ends, within the
builder's grace) and the chart should end the minute on the real one.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Protocol

from channelflow.bars import Bar
from channelflow.live.messages import DEFAULT_TOPICS, Topics, key_for, live_bar_from_bar, to_record
from channelflow.transport import Record

logger = logging.getLogger(__name__)

SECOND_NS = 1_000_000_000

#: How often a series' forming bar may be published: four times a second. The chart updates its
#: last candle as the price moves, and a second between updates looked like a price that did not
#: (REQ-WP-108); the browser coalesces what it is sent.
FORMING_INTERVAL_NS = SECOND_NS // 4


class _Broker(Protocol):
    def publish(self, record: Record) -> None: ...


class LivePublisher:
    def __init__(
        self,
        broker: _Broker | None,
        *,
        producer: str,
        now_ns: Callable[[], int],
        topics: Topics = DEFAULT_TOPICS,
    ) -> None:
        self._broker = broker
        self._producer = producer
        self._topics = topics
        self._now = now_ns
        self._last_forming: dict[str, int] = {}
        #: What each series' forming bar last was when published; an unchanged one is not resent.
        self._last_shape: dict[str, tuple[object, ...]] = {}
        self.published = 0
        self.failures = 0

    @property
    def enabled(self) -> bool:
        return self._broker is not None

    def forming(self, bars: Sequence[Bar]) -> None:
        """Publish the forming bars: each series at most four times a second, only when changed."""
        if self._broker is None or not bars:
            return
        now = self._now()
        for bar in bars:
            key = key_for(bar.venue, bar.symbol)
            last = self._last_forming.get(key)
            if last is not None and now - last < FORMING_INTERVAL_NS:
                continue
            shape = (bar.open_time_ns, bar.open, bar.high, bar.low, bar.close, bar.volume_base)
            if self._last_shape.get(key) == shape:
                # Nothing traded since it was last sent: the same bar four times a second is noise.
                continue
            if self._send(bar, now):
                self._last_forming[key] = now
                self._last_shape[key] = shape

    def final(self, bar: Bar) -> None:
        """Publish a finished bar, always."""
        if self._broker is not None:
            self._send(bar, self._now())

    def _send(self, bar: Bar, now: int) -> bool:
        assert self._broker is not None
        try:
            self._broker.publish(
                to_record(
                    live_bar_from_bar(bar),
                    ingest_time_ns=now,
                    producer=self._producer,
                    topics=self._topics,
                )
            )
        except Exception as exc:  # noqa: BLE001 -- the view must never cost the ingest a trade
            self.failures += 1
            if self.failures == 1 or self.failures % 1000 == 0:
                logger.warning(
                    "live bar not published (%d so far): %s: %s",
                    self.failures,
                    type(exc).__name__,
                    exc,
                )
            return False
        self.published += 1
        return True
