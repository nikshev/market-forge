"""The live feed through a real broker: ingest publisher -> topic -> API relay (REQ-WP-102).

The unit suite proves the cache, the precedence rules and the relay over the in-process transport;
this proves the same path over Kafka's protocol -- the topic is created with its retention, a
produced bar comes back as the same bar, and a late-joining consumer reads what was published
before it arrived (which is how the API rebuilds its cache on every start).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import suppress

import pytest

from channelflow.live.broker import RETENTION_MS, broker_for, consumer_for, ensure_topic
from channelflow.live.publisher import LivePublisher
from channelflow.live.relay import LiveCache, LiveRelay
from tests.integration.test_transport_on_redpanda import _env
from tests.unit.live.test_messages import MINUTE, T0, bar

pytestmark = [pytest.mark.integration, pytest.mark.trace("REQ-WP-102")]


@pytest.fixture
def bootstrap() -> str:
    address = f"127.0.0.1:{_env()['REDPANDA_PORT']}"
    try:
        from confluent_kafka.admin import AdminClient

        AdminClient({"bootstrap.servers": address}).list_topics(timeout=5)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"The broker is not answering on {address}: {exc}. Run `make up`.")
    return address


@pytest.fixture
def topic(bootstrap: str) -> Iterator[str]:
    name = f"market.bar_live_{uuid.uuid4().hex[:8]}.v1"
    yield name
    from confluent_kafka.admin import AdminClient

    for future in (
        AdminClient({"bootstrap.servers": bootstrap})
        .delete_topics([name], operation_timeout=10)
        .values()
    ):
        with suppress(Exception):
            future.result(timeout=10)


def test_the_topic_is_created_with_the_cache_windows_retention(bootstrap: str, topic: str) -> None:
    from confluent_kafka.admin import AdminClient, ConfigResource

    assert ensure_topic(bootstrap, topic=topic) is True
    assert ensure_topic(bootstrap, topic=topic) is True, "creating it twice is not an error"

    admin = AdminClient({"bootstrap.servers": bootstrap})
    resource = ConfigResource(ConfigResource.Type.TOPIC, topic)
    config = next(iter(admin.describe_configs([resource]).values())).result(timeout=10)
    assert config["retention.ms"].value == str(RETENTION_MS)


def test_a_bar_published_before_the_consumer_arrived_is_still_relayed(
    bootstrap: str, topic: str
) -> None:
    clock = [T0]
    broker = broker_for(bootstrap, topic=topic)
    live = LivePublisher(broker, producer="test", now_ns=lambda: clock[0], topic=topic)
    live.final(bar(final=True, close="105", open_time=T0))
    live.forming([bar(final=False, close="106", open_time=T0 + MINUTE)])
    broker._client.flush(10)  # noqa: SLF001 -- the test waits for delivery; the ingest never does

    sent: list[str] = []
    relay = LiveRelay(
        consumer_for(bootstrap, topic=topic), LiveCache(), lambda b: sent.append(b.close)
    )
    deadline = time.monotonic() + 30
    while len(sent) < 2 and time.monotonic() < deadline:
        relay.run_once(timeout=2.0)

    assert sent == ["105", "106"]
    assert [b.close for b in relay.cache.snapshot("bybit", "BTCUSDT")] == ["105", "106"]
    assert live.published == 2 and live.failures == 0
