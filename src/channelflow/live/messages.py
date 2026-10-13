"""What travels from the ingest to the chart (REQ-WP-102).

# @trace: REQ-WP-102
# @trace: REQ-WP-108

The wire form is the REST bars' (`BarOut`): nanosecond instants as **strings** (a JSON number
cannot hold one exactly), prices as decimal strings, and `is_final`. The venue and symbol are
added, because one topic carries every series.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from channelflow.bars import Bar
from channelflow.transport import Record

#: Versioned, as section 6.4.3 requires of every topic. **Two**, because they are read differently
# (REQ-WP-108): the : finished bars -- one a minute per series -- are replayed from the start to
# rebuild the API's cache, a few hundred : records; the forming bars -- up to four a second per
# series -- are only ever read as they arrive. On one topic every : start replayed hours of forming
# bars, and the chart showed nothing moving for forty seconds.
TOPIC_FINAL = "market.bar_final.v1"
TOPIC_FORMING = "market.bar_forming.v1"


class Topics(NamedTuple):
    final: str
    forming: str


DEFAULT_TOPICS = Topics(final=TOPIC_FINAL, forming=TOPIC_FORMING)


def topic_for(live: LiveBar, topics: Topics = DEFAULT_TOPICS) -> str:
    return topics.final if live.is_final else topics.forming


_FIELDS = (
    "venue",
    "symbol",
    "open_time_ns",
    "close_time_ns",
    "open",
    "high",
    "low",
    "close",
    "volume_base",
    "is_final",
)


@dataclass(frozen=True)
class LiveBar:
    venue: str
    symbol: str
    open_time_ns: str
    close_time_ns: str
    open: str
    high: str
    low: str
    close: str
    volume_base: str
    is_final: bool

    def as_wire(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in _FIELDS}


def key_for(venue: str, symbol: str) -> str:
    return f"{venue}:{symbol}"


def live_bar_from_bar(bar: Bar) -> LiveBar:
    return LiveBar(
        venue=bar.venue,
        symbol=bar.symbol,
        open_time_ns=str(bar.open_time_ns),
        close_time_ns=str(bar.close_time_ns),
        open=str(bar.open),
        high=str(bar.high),
        low=str(bar.low),
        close=str(bar.close),
        volume_base=str(bar.volume_base),
        is_final=bar.is_final,
    )


def to_record(
    live: LiveBar, *, ingest_time_ns: int, producer: str, topics: Topics = DEFAULT_TOPICS
) -> Record:
    return Record(
        topic=topic_for(live, topics),
        key=key_for(live.venue, live.symbol),
        payload=live.as_wire(),
        # The window's end: the instant the bar is about, which the ingest time (when it was said)
        # is not.
        event_time_ns=int(live.close_time_ns),
        ingest_time_ns=ingest_time_ns,
        producer=producer,
    )


def parse_record(record: Record) -> LiveBar:
    payload = record.payload
    missing = [name for name in _FIELDS if name not in payload]
    if missing:
        raise ValueError(f"not a live bar: missing {', '.join(missing)}")
    return LiveBar(
        venue=str(payload["venue"]),
        symbol=str(payload["symbol"]),
        open_time_ns=str(payload["open_time_ns"]),
        close_time_ns=str(payload["close_time_ns"]),
        open=str(payload["open"]),
        high=str(payload["high"]),
        low=str(payload["low"]),
        close=str(payload["close"]),
        volume_base=str(payload["volume_base"]),
        is_final=bool(payload["is_final"]),
    )
