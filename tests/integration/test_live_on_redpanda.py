"""The live feed through a real broker (REQ-WP-102, REQ-WP-108).

The unit suite proves the cache, the precedence rules and the relay over the in-process transport;
this proves the same path over Kafka's protocol: the topics get the retention they were asked for
-- including a topic that already existed with a default one, which the first deployed run found
keeping seven days of bars -- the finals published before a consumer arrived are replayed to it,
and a forming bar published after it started is delivered at once, not a second later.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import suppress

import pytest

from channelflow.live.broker import (
    FINAL_RETENTION_MS,
    FORMING_RETENTION_MS,
    broker_for,
    consumers_for,
    ensure_topic,
    ensure_topics,
)
from channelflow.live.messages import Topics
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
def topics(bootstrap: str) -> Iterator[Topics]:
    unique = uuid.uuid4().hex[:8]
    names = Topics(final=f"market.bar_final_{unique}.v1", forming=f"market.bar_forming_{unique}.v1")
    yield names
    from confluent_kafka.admin import AdminClient

    # The client is held in a name until the deletes have finished: a temporary is collected at
    # once, and the request with it -- which is how every run of this file left its topics behind.
    admin = AdminClient({"bootstrap.servers": bootstrap})
    for future in admin.delete_topics(list(names), operation_timeout=10).values():
        with suppress(Exception):
            future.result(timeout=10)


def retention_of(bootstrap: str, topic: str) -> str:
    from confluent_kafka.admin import AdminClient, ConfigResource

    admin = AdminClient({"bootstrap.servers": bootstrap})
    resource = ConfigResource(ConfigResource.Type.TOPIC, topic)
    config = next(iter(admin.describe_configs([resource]).values())).result(timeout=10)
    return str(config["retention.ms"].value)


def test_the_topics_are_created_with_their_retentions(bootstrap: str, topics: Topics) -> None:
    assert ensure_topics(bootstrap, topics) is True
    assert ensure_topics(bootstrap, topics) is True, "creating them twice is not an error"

    assert retention_of(bootstrap, topics.final) == str(FINAL_RETENTION_MS)
    assert retention_of(bootstrap, topics.forming) == str(FORMING_RETENTION_MS)


def test_a_topic_that_already_exists_with_another_retention_is_brought_to_the_asked_one(
    bootstrap: str, topics: Topics
) -> None:
    """The first deployed run: a seven-day default on a topic meant for thirty minutes."""
    from confluent_kafka.admin import AdminClient, NewTopic

    admin = AdminClient({"bootstrap.servers": bootstrap})
    for future in admin.create_topics([NewTopic(topics.final, 1, 1)]).values():
        future.result(timeout=10)
    assert retention_of(bootstrap, topics.final) != str(FINAL_RETENTION_MS)

    assert ensure_topic(bootstrap, topic=topics.final, retention_ms=FINAL_RETENTION_MS) is True

    assert retention_of(bootstrap, topics.final) == str(FINAL_RETENTION_MS)


def test_a_final_published_before_the_consumer_arrived_is_replayed_and_not_forwarded(
    bootstrap: str, topics: Topics
) -> None:
    broker = broker_for(bootstrap, topics=topics)
    live = LivePublisher(broker, producer="test", now_ns=lambda: T0, topics=topics)
    live.final(bar(final=True, close="105", open_time=T0))
    broker._client.flush(10)  # noqa: SLF001 -- the test waits for delivery; the ingest never does

    finals, forming = consumers_for(bootstrap, topics=topics)
    sent: list[str] = []
    relay = LiveRelay(finals, LiveCache(), lambda b: sent.append(b.close), tail=forming)
    deadline = time.monotonic() + 30
    while not relay.cache.snapshot("bybit", "BTCUSDT") and time.monotonic() < deadline:
        relay.run_once(timeout=2.0, forward=False)

    assert [b.close for b in relay.cache.snapshot("bybit", "BTCUSDT")] == ["105"]
    assert sent == []


def test_a_forming_bar_published_after_the_consumer_started_is_delivered_promptly(
    bootstrap: str, topics: Topics
) -> None:
    broker = broker_for(bootstrap, topics=topics)
    finals, forming = consumers_for(bootstrap, topics=topics)
    sent: list[tuple[str, float]] = []
    relay = LiveRelay(
        finals, LiveCache(), lambda b: sent.append((b.close, time.monotonic())), tail=forming
    )
    # Let the groups join before the bar is published: a "latest" consumer starts at the end.
    for _ in range(40):
        relay._take(forming, limit=10, timeout=0.25, forward=False)  # noqa: SLF001
        if getattr(forming, "client", None) is not None and forming.client.assignment():  # type: ignore[attr-defined]
            break

    live = LivePublisher(broker, producer="test", now_ns=lambda: T0 + MINUTE, topics=topics)
    published_at = time.monotonic()
    live.forming([bar(final=False, close="106", open_time=T0 + MINUTE)])
    deadline = time.monotonic() + 10
    while not sent and time.monotonic() < deadline:
        relay._take(forming, limit=500, timeout=0.1, forward=True)  # noqa: SLF001

    assert [close for close, _ in sent] == ["106"]
    assert sent[0][1] - published_at < 3.0, (
        "a forming bar was held for seconds before it was delivered"
    )
