"""The in-process half of PRD section 6.3's pair.

# @trace: REQ-WP-042

Not a mock. Section 6.3 asks for two implementations of one interface, and this
is one of them -- the one the MVP runs on, and the one the fast gate uses
because it needs no broker (REQ-INFRA-002).

Each consumer keeps its own position, so two consumers of one topic both see
everything, which is what a log is. A queue that handed each record to exactly
one consumer would be a different thing wearing the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from channelflow.transport import EventConsumer, EventPublisher, Record


@dataclass
class InProcessTransport:
    """One log per topic, in memory."""

    _topics: dict[str, list[Record]] = field(default_factory=dict)

    def publisher(self) -> EventPublisher:
        return _Publisher(self)

    def consumer(self, topics: list[str]) -> EventConsumer:
        return _Consumer(self, tuple(topics))

    def _append(self, record: Record) -> None:
        self._topics.setdefault(record.topic, []).append(record)

    def _read(self, topic: str, offset: int, limit: int) -> list[Record]:
        return self._topics.get(topic, [])[offset : offset + limit]


@dataclass
class _Publisher:
    transport: InProcessTransport

    def publish(self, record: Record) -> None:
        self.transport._append(record)

    def flush(self) -> None:
        """Nothing is buffered, and the method exists anyway.

        A caller that had to know which implementation it held in order to know
        whether to flush would be branching on the transport, which is the thing
        the port exists to prevent.
        """


@dataclass
class _Consumer:
    transport: InProcessTransport
    topics: tuple[str, ...]
    _offsets: dict[str, int] = field(default_factory=dict)

    def poll(self, *, limit: int) -> list[Record]:
        found: list[Record] = []
        for topic in self.topics:
            offset = self._offsets.get(topic, 0)
            batch = self.transport._read(topic, offset, limit - len(found))
            self._offsets[topic] = offset + len(batch)
            found.extend(batch)
            if len(found) >= limit:
                break
        return found
