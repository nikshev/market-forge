"""PRD section 6.3's `EventPublisher`/`EventConsumer`, and what travels on them.

# @trace: REQ-WP-042

Section 6.3 is explicit about the shape:

    Але interfaces будуються так, щоб `EventPublisher/EventConsumer` мали
    in-process та Kafka implementations.

    (But the interfaces are built so that `EventPublisher`/`EventConsumer` have
    in-process and Kafka implementations.)

[[ADR-063]] settled the rest: Kafka protocol, Redpanda on the stack, and the
Parquet written by a consumer in this repository rather than by a connector --
because a connector would write our tables while knowing none of our rules.

**A record carries what section 6.4.3 says it carries**, and two of those are
checked here rather than hoped for. The topic's schema version is explicit,
because a topic named `market.trade` says nothing about which shape its payload
has and the first schema change would be silent. And the partition key is
present, because ordering is per key and a record without one has no ordering
guarantee to lose.

**Event time and ingestion time are two fields, always.** PRD section 9 forbids
a feature treating ingest time as market information; one timestamp doing both
jobs would leave nothing downstream able to tell them apart. An ingestion time
earlier than its event time is *accepted*: clocks disagree, and a transport that
quietly repaired the disagreement would hide it from the only people who could
fix it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

#: Section 6.4.3's naming: source, semantic type and an explicit schema version.
_TOPIC = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*\.v[0-9]+$")


class UnversionedTopic(ValueError):
    """A topic name with no schema version.

    Section 6.4.3 requires it to be explicit. Without it a payload's shape is
    whatever the last deploy decided, and the first change is silent.
    """


class NoPartitionKey(ValueError):
    """A record with nothing to order it by."""


class NoProducer(ValueError):
    """A record that does not say who wrote it.

    Section 6.4.3 asks for producer and sequence metadata to be retained; an
    anonymous record makes a gap impossible to attribute.
    """


@dataclass(frozen=True)
class Record:
    """One event on the wire."""

    topic: str
    #: Normally `venue:symbol` or `chain:pool` (section 6.4.3).
    key: str
    payload: Mapping[str, object]
    #: Assigned by the source. The only clock a feature may use.
    event_time_ns: int
    #: When we received it. Never market information -- PRD section 9.
    ingest_time_ns: int
    producer: str
    #: Where a source has one. `None` is "this source does not number its
    #: events", which is a different fact from "the number is zero".
    sequence: int | None = None
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _TOPIC.match(self.topic):
            raise UnversionedTopic(
                f"{self.topic!r} carries no schema version; section 6.4.3 requires one, "
                "and without it the first payload change is silent"
            )
        if not self.key.strip():
            raise NoPartitionKey(
                f"a record on {self.topic} has no partition key; ordering is per key"
            )
        if not self.producer.strip():
            raise NoProducer(f"a record on {self.topic} does not say who produced it")
        if self.event_time_ns < 0 or self.ingest_time_ns < 0:
            raise ValueError("a timestamp before the epoch describes nothing")


class EventPublisher(Protocol):
    """Whatever records go into."""

    def publish(self, record: Record) -> None: ...

    def flush(self) -> None:
        """Make published records visible to consumers.

        Named rather than implied: a Kafka producer batches, and a caller that
        did not know to flush would watch a test hang on an empty poll.
        """
        ...


class EventConsumer(Protocol):
    """Whatever records come out of."""

    def poll(self, *, limit: int) -> list[Record]:
        """Up to `limit` records. An empty list is an answer."""
        ...


__all__ = [
    "EventConsumer",
    "EventPublisher",
    "NoPartitionKey",
    "NoProducer",
    "Record",
    "UnversionedTopic",
]
