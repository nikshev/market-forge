"""The broker end of the live feed: a producer that cannot hold a trade up, and the consumers
(REQ-WP-102).

# @trace: REQ-WP-102
# @trace: REQ-WP-108

Redpanda on the dev stack ([[ADR-063]]); this speaks the Kafka protocol and knows nothing else about
it.

The topics are created here, with one partition and a **retention that is enforced, not merely
asked for**: a topic that already existed -- made by auto-creation, or by an earlier build -- keeps
the retention it was made with unless it is altered, and the first deployed run found a seven-day
default on a topic meant to hold thirty minutes, so every API start replayed days of bars. The
finals keep thirty minutes (the cache's window) and the forming bars five (nothing reads them after
the second they arrive). Creation is idempotent and a failure is not fatal -- a feed that cannot
start is a chart that says "delayed".
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from typing import Any

from channelflow.live.messages import DEFAULT_TOPICS, Topics
from channelflow.transport import EventConsumer, Record
from channelflow.transport.kafka import KafkaTransport, _headers

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = "CHANNELFLOW_KAFKA_BOOTSTRAP"
FINAL_RETENTION_MS = 30 * 60 * 1000
FORMING_RETENTION_MS = 5 * 60 * 1000


def bootstrap_from_env(environ: Mapping[str, str]) -> str | None:
    """The broker's address, or `None`: unset or empty means no live feed, which is not an error."""
    value = environ.get(KAFKA_BOOTSTRAP, "").strip()
    return value or None


def retention_for(topic: str, topics: Topics = DEFAULT_TOPICS) -> int:
    return FINAL_RETENTION_MS if topic == topics.final else FORMING_RETENTION_MS


def ensure_topic(bootstrap: str, *, topic: str, retention_ms: int, timeout: float = 10.0) -> bool:
    """Make the topic exist with this retention. `True` if it does afterwards."""
    from confluent_kafka import KafkaError
    from confluent_kafka.admin import (  # type: ignore[attr-defined]
        AdminClient,
        AlterConfigOpType,
        ConfigEntry,
        ConfigResource,
        NewTopic,
    )

    try:
        client = AdminClient({"bootstrap.servers": bootstrap})
        futures = client.create_topics(
            [
                NewTopic(
                    topic,
                    num_partitions=1,
                    replication_factor=1,
                    config={"retention.ms": str(retention_ms)},
                )
            ],
            request_timeout=timeout,
        )
        existed = False
        for future in futures.values():
            try:
                future.result(timeout=timeout)
            except Exception as exc:  # noqa: BLE001 -- "already exists" is the usual answer
                error = exc.args[0] if exc.args else None
                if getattr(error, "code", lambda: None)() != KafkaError.TOPIC_ALREADY_EXISTS:
                    raise
                existed = True
        if existed:
            resource = ConfigResource(
                ConfigResource.Type.TOPIC,
                topic,
                incremental_configs=[
                    ConfigEntry(
                        "retention.ms",
                        str(retention_ms),
                        incremental_operation=AlterConfigOpType.SET,
                    )
                ],
            )
            for future in client.incremental_alter_configs([resource]).values():
                future.result(timeout=timeout)
    except Exception as exc:  # noqa: BLE001 -- a broker not there yet is the caller's to retry
        logger.warning("live feed: could not ensure topic %s on %s: %s", topic, bootstrap, exc)
        return False
    return True


def ensure_topics(bootstrap: str, topics: Topics = DEFAULT_TOPICS) -> bool:
    ok = ensure_topic(bootstrap, topic=topics.final, retention_ms=FINAL_RETENTION_MS)
    return ensure_topic(bootstrap, topic=topics.forming, retention_ms=FORMING_RETENTION_MS) and ok


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


def broker_for(bootstrap: str, *, topics: Topics = DEFAULT_TOPICS) -> KafkaBroker:
    from confluent_kafka import Producer

    ensure_topics(bootstrap, topics)
    return KafkaBroker(
        Producer(
            {
                "bootstrap.servers": bootstrap,
                "linger.ms": 5,
                "queue.buffering.max.messages": 20_000,
                # Past this a message is dropped rather than held: a view is not worth the memory.
                "message.timeout.ms": 10_000,
                "delivery.report.only.error": True,
            }
        )
    )


def consumers_for(
    bootstrap: str, *, topics: Topics = DEFAULT_TOPICS
) -> tuple[EventConsumer, EventConsumer]:
    """`(finals, forming)`: the finals from the start of their topic, the forming bars from now.

    A group of its own for each, so every API start reads the finals again (a few hundred records)
    and reads no forming bar it did not see arrive.
    """
    ensure_topics(bootstrap, topics)
    group = f"api-live-{uuid.uuid4().hex[:12]}"
    finals = KafkaTransport(bootstrap).consumer([topics.final], group=f"{group}-final")
    forming = KafkaTransport(bootstrap, options={"auto.offset.reset": "latest"}).consumer(
        [topics.forming], group=f"{group}-forming"
    )
    return finals, forming
