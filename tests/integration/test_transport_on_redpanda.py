"""The Kafka half of the event backbone, against a real broker (REQ-WP-042).

PRD §6.3 asks for one interface with two implementations. The unit suite proves
the in-process one; this proves the other, and it does so by importing the same
test bodies rather than restating them.

That matters more than it looks. A test written against one implementation and
read as proof of the interface is exactly what [[REQ-WP-041]] found in the
catalog work -- the claim and its evidence in different files, neither knowing
about the other. Here the evidence is literally the same function.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest

from channelflow.transport.kafka import KafkaTransport
from tests.unit.transport.test_transport import (
    empty_poll_is_an_answer,
    order_within_a_key,
    round_trip,
)


def _env() -> dict[str, str]:
    values: dict[str, str] = {}
    # `.env.example` first as the documented defaults, `.env` over it as the
    # developer's overrides. An earlier version read whichever existed and
    # stopped, so a key added to the example -- a new service, say -- was
    # missing on every checkout whose `.env` predated it, and the failure said
    # `KeyError` rather than "copy the new line".
    for name in (".env.example", ".env"):
        path = Path(__file__).resolve().parents[2] / name
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    values.update({k: v for k, v in os.environ.items() if k in values})
    return values


@pytest.fixture
def transport() -> KafkaTransport:
    env = _env()
    bootstrap = f"127.0.0.1:{env['REDPANDA_PORT']}"
    try:
        from confluent_kafka.admin import AdminClient

        AdminClient({"bootstrap.servers": bootstrap}).list_topics(timeout=5)
    except Exception as exc:  # noqa: BLE001 -- the stack being down is the
        # failure worth naming; a client error alone sends somebody to the
        # wrong question.
        pytest.fail(f"The broker is not answering on {bootstrap}: {exc}. Run `make up`.")
    return KafkaTransport(bootstrap=bootstrap)


@pytest.fixture
def topic(transport: KafkaTransport) -> Iterator[str]:
    """A fresh topic per test, **removed afterwards**.

    Fresh, because a reused topic would let one test consume another run's
    records and pass for the wrong reason -- the same rule the object-store
    fixtures follow with prefixes.

    Removed, because a broker outlives the test run. This leaked one topic per
    test for months and the cost was invisible until it was total: measured at
    259 abandoned topics, the development broker answered

        Refusing to create 1 new partition replicas as total partition replica
        count 263 would exceed memory limit of 262 partition replicas

    and stopped creating them. The consumer then subscribes to a topic that does
    not exist, the poll returns nothing, and the failure reads `assert [] ==
    [1, 2, 3]` -- which says nothing whatever about topics. CI never saw it: its
    broker is new every run, which is exactly the shape of defect a disposable
    environment hides.
    """
    name = f"market.trade_{uuid.uuid4().hex[:8]}.v1"
    yield name
    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": transport.bootstrap})
    for future in admin.delete_topics([name], operation_timeout=10).values():
        with suppress(Exception):  # the test may never have created it
            future.result(timeout=10)


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-042")
def test_a_record_survives_the_round_trip(transport: KafkaTransport, topic: str) -> None:
    round_trip(
        transport.publisher(),
        transport.consumer([topic], group=f"g-{uuid.uuid4().hex[:8]}"),
        topic=topic,
    )


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-042")
def test_an_empty_poll_is_an_answer(transport: KafkaTransport, topic: str) -> None:
    empty_poll_is_an_answer(
        transport.publisher(),
        transport.consumer([topic], group=f"g-{uuid.uuid4().hex[:8]}"),
        topic=topic,
    )


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-042")
def test_records_come_back_in_order_within_a_key(transport: KafkaTransport, topic: str) -> None:
    """Ordering is per partition key, and on a real broker that is a property of
    the partition rather than of a list."""
    order_within_a_key(
        transport.publisher(),
        transport.consumer([topic], group=f"g-{uuid.uuid4().hex[:8]}"),
        topic=topic,
    )
