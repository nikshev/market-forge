"""The Kafka-protocol half of PRD section 6.3's pair.

# @trace: REQ-WP-042

The other implementation of the same interface. Nothing that publishes or
consumes knows which one it holds -- that is section 6.3's whole request, and
the unit suite checks it by running one test body over both.

The broker is Redpanda on the dev stack ([[ADR-063]]) and this file does not
know that. It speaks the protocol, which is why the broker choice costs a
compose file to reverse rather than a rewrite.

Payloads are JSON. Section 6.4.3 requires the schema version to be explicit and
the topic name carries it; a binary format with a registry is a different
guarantee and a different service, and the requirement says so.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from confluent_kafka import KafkaError

from channelflow.transport import EventConsumer, EventPublisher, Record

#: Errors that mean "nothing yet" rather than "something went wrong". The topic
#: a consumer subscribed to may not have been produced to, and a partition may
#: simply be caught up; neither is a fault, and both arrive as an error object.
_NOT_YET = frozenset({KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART})

#: Header names. Section 6.4.3 asks for event and ingestion time to stay apart,
#: and for producer and sequence metadata to be retained; the payload is the
#: caller's and these do not live inside it.
EVENT_TIME = "event_time_ns"
INGEST_TIME = "ingest_time_ns"
PRODUCER = "producer"
SEQUENCE = "sequence"


@dataclass
class KafkaTransport:
    """Publishers and consumers against a Kafka-protocol broker."""

    bootstrap: str
    #: Everything else the client takes. Passed through rather than
    #: interpreted: the moment this knew what a security protocol was, it would
    #: be the place every deployment's options went.
    options: dict[str, Any] = field(default_factory=dict)

    def publisher(self) -> EventPublisher:
        from confluent_kafka import Producer

        return _Publisher(Producer({"bootstrap.servers": self.bootstrap, **self.options}))

    def consumer(self, topics: list[str], *, group: str) -> EventConsumer:
        from confluent_kafka import Consumer

        client = Consumer(
            {
                "bootstrap.servers": self.bootstrap,
                "group.id": group,
                # From the beginning: a consumer that joined and skipped what
                # was already there would materialise a partial history and
                # look like it had worked.
                "auto.offset.reset": "earliest",
                **self.options,
            }
        )
        client.subscribe(topics)
        return _Consumer(client)


@dataclass
class _Publisher:
    client: Any

    def publish(self, record: Record) -> None:
        self.client.produce(
            topic=record.topic,
            key=record.key.encode(),
            value=json.dumps(dict(record.payload), sort_keys=True).encode(),
            headers=_headers(record),
        )

    def flush(self) -> None:
        self.client.flush()


@dataclass
class _Consumer:
    client: Any

    def poll(self, *, limit: int, timeout: float = 8.0) -> list[Record]:
        """Up to `limit` records, waiting at most `timeout` for the first.

        Consuming in a loop until the deadline rather than once: a group's first
        `consume` often returns empty while the assignment is still being made,
        and a caller reading that as "the topic is empty" would be believing a
        rebalance. Once anything has arrived this returns it rather than waiting
        for a full batch -- `limit` is a ceiling, not a quota.
        """
        import time

        deadline = time.monotonic() + timeout
        found: list[Record] = []
        while not found and time.monotonic() < deadline:
            messages = self.client.consume(
                num_messages=limit, timeout=max(0.1, deadline - time.monotonic())
            )
            found.extend(self._decode(messages))
        return found

    def _decode(self, messages: list[Any]) -> list[Record]:
        found: list[Record] = []
        for message in messages:
            error = message.error()
            if error is not None:
                if error.code() in _NOT_YET:
                    # Not a failure. "The topic does not exist yet" and "this
                    # partition has no more for now" are both the case the spec
                    # calls ordinary: a consumer starting before a producer.
                    #
                    # Named rather than swallowed. Every other error is raised,
                    # because a consumer that dropped them would report an empty
                    # poll and an empty poll reads as "nothing happened".
                    continue
                raise RuntimeError(f"consuming {message.topic()}: {error}")
            found.append(_record(message))
        return found


def _headers(record: Record) -> list[tuple[str, bytes]]:
    headers = [
        (EVENT_TIME, str(record.event_time_ns).encode()),
        (INGEST_TIME, str(record.ingest_time_ns).encode()),
        (PRODUCER, record.producer.encode()),
    ]
    # Absent rather than zero: "this source does not number its events" and
    # "the number is zero" are different facts.
    if record.sequence is not None:
        headers.append((SEQUENCE, str(record.sequence).encode()))
    headers += [(name, value.encode()) for name, value in record.headers.items()]
    return headers


def _record(message: Any) -> Record:
    headers = {name: value for name, value in (message.headers() or [])}
    extra = {
        name.decode() if isinstance(name, bytes) else name: value.decode()
        for name, value in headers.items()
        if (name.decode() if isinstance(name, bytes) else name)
        not in {EVENT_TIME, INGEST_TIME, PRODUCER, SEQUENCE}
    }
    sequence = headers.get(SEQUENCE)
    return Record(
        topic=message.topic(),
        key=message.key().decode(),
        payload=json.loads(message.value().decode()),
        event_time_ns=int(headers[EVENT_TIME]),
        ingest_time_ns=int(headers[INGEST_TIME]),
        producer=headers[PRODUCER].decode(),
        sequence=None if sequence is None else int(sequence),
        headers=extra,
    )
