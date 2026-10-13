"""The broker end of the live feed: a producer that cannot hold a trade up, and a consumer
(REQ-WP-102).

# @trace: REQ-WP-102

Redpanda on the dev stack ([[ADR-063]]); this speaks the Kafka protocol and knows nothing else about
it.

The topic is created here, with **thirty minutes' retention and one partition**: the API's cache is
rebuilt on each start by reading it from the beginning, so its retention is the cache's window and a
longer one would only make a restart slower. Creation is idempotent and a failure is not fatal --
Redpanda may create it on first use, and a feed that cannot start is a chart that says "delayed".
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from typing import Any

from channelflow.live.messages import TOPIC
from channelflow.transport import EventConsumer, Record
from channelflow.transport.kafka import KafkaTransport, _headers

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "CHANNELFLOW_KAFKA_BOOTSTRAP"
RETENTION_MS = 30 * 60 * 1000


def bootstrap_from_env(environ: Mapping[str, str]) -> str | None:
    """The broker's address, or `None`: unset or empty means no live feed, which is not an error."""
    value = environ.get(KAFKA_BOOTSTRAP, "").strip()
    return value or None


def ensure_topic(bootstrap: str, *, timeout: float = 10.0, topic: str = TOPIC) -> bool:
    """Create the live topic if it is not there. `True` if it is there afterwards."""
    from confluent_kafka import KafkaError
    from confluent_kafka.admin import AdminClient, NewTopic  # type: ignore[attr-defined]

    try:
        client = AdminClient({"bootstrap.servers": bootstrap})
        futures = client.create_topics(
            [
                NewTopic(
                    topic,
                    num_partitions=1,
                    replication_factor=1,
                    config={"retention.ms": str(RETENTION_MS)},
                )
            ],
            request_timeout=timeout,
        )
        for future in futures.values():
            try:
                future.result(timeout=timeout)
            except Exception as exc:  # noqa: BLE001 -- "already exists" is the usual answer
                error = exc.args[0] if exc.args else None
                if getattr(error, "code", lambda: None)() != KafkaError.TOPIC_ALREADY_EXISTS:
                    raise
    except Exception as exc:  # noqa: BLE001 -- a broker not there yet is the caller's to retry
        logger.warning("live feed: could not ensure topic %s on %s: %s", topic, bootstrap, exc)
        return False
    return True


class KafkaBroker:
    """`publish(record)` that returns at once.

    `produce` only queues; a full queue raises `BufferError`, which the publisher counts. Delivery
    reports are not wanted (a lost live bar costs a candle the table supplies later), so they are
    switched off and `poll(0)` only keeps the client's own bookkeeping moving.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def publish(self, record: Record) -> None:
        import json

        self._client.produce(
            topic=record.topic,
            key=record.key.encode(),
            value=json.dumps(dict(record.payload), sort_keys=True).encode(),
            headers=_headers(record),
        )
        self._client.poll(0)


def broker_for(bootstrap: str, *, topic: str = TOPIC) -> KafkaBroker:
    from confluent_kafka import Producer

    ensure_topic(bootstrap, topic=topic)
    return KafkaBroker(
        Producer(
            {
                "bootstrap.servers": bootstrap,
                "linger.ms": 20,
                "queue.buffering.max.messages": 20_000,
                # Past this a message is dropped rather than held: a view is not worth the memory.
                "message.timeout.ms": 10_000,
                "delivery.report.only.error": True,
            }
        )
    )


def consumer_for(bootstrap: str, *, topic: str = TOPIC) -> EventConsumer:
    """A consumer of the whole retained topic, in a group of its own: each start replays it."""
    ensure_topic(bootstrap, topic=topic)
    return KafkaTransport(bootstrap).consumer([topic], group=f"api-live-{uuid.uuid4().hex[:12]}")
