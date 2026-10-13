"""The ingest's side: forming bars at most once a second, finals always, and never a stopped ingest
(REQ-WP-102)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from channelflow.live.messages import TOPIC, parse_record
from channelflow.live.publisher import LivePublisher
from channelflow.transport import Record
from tests.unit.live.test_messages import MINUTE, T0, bar

pytestmark = pytest.mark.trace("REQ-WP-102")

SECOND = 1_000_000_000


@dataclass
class Broker:
    records: list[Record] = field(default_factory=list)
    fail: bool = False

    def publish(self, record: Record) -> None:
        if self.fail:
            raise BufferError("local queue full")
        self.records.append(record)

    def flush(self) -> None:
        pass


def publisher(broker: Broker, now: list[int]) -> LivePublisher:
    return LivePublisher(broker, producer="ingest-bybit", now_ns=lambda: now[0])


def test_a_forming_bar_is_published_to_the_live_topic_keyed_by_series() -> None:
    broker, now = Broker(), [T0 + SECOND]

    publisher(broker, now).forming([bar(final=False)])

    (record,) = broker.records
    assert (record.topic, record.key) == (TOPIC, "bybit:BTCUSDT")
    assert parse_record(record).is_final is False
    assert record.ingest_time_ns == T0 + SECOND


def test_forming_bars_are_published_at_most_once_a_second() -> None:
    broker, now = Broker(), [T0]
    live = publisher(broker, now)

    live.forming([bar(final=False)])
    now[0] += SECOND // 2
    live.forming([bar(final=False, close="102")])
    assert len(broker.records) == 1

    now[0] += SECOND // 2
    live.forming([bar(final=False, close="103")])
    assert len(broker.records) == 2
    assert parse_record(broker.records[-1]).close == "103"


def test_a_final_bar_is_always_published_even_inside_the_second() -> None:
    broker, now = Broker(), [T0]
    live = publisher(broker, now)
    live.forming([bar(final=False)])

    live.final(bar(final=True))

    assert [parse_record(r).is_final for r in broker.records] == [False, True]


def test_a_final_bar_does_not_wait_for_the_forming_throttle_of_the_next_minute() -> None:
    broker, now = Broker(), [T0]
    live = publisher(broker, now)

    live.final(bar(final=True))
    live.forming([bar(final=False, open_time=T0 + MINUTE)])

    assert len(broker.records) == 2


def test_a_broker_that_raises_stops_nothing_and_is_counted() -> None:
    broker, now = Broker(fail=True), [T0]
    live = publisher(broker, now)

    live.forming([bar(final=False)])
    live.final(bar(final=True))

    assert live.failures == 2
    assert live.published == 0


def test_a_failure_is_not_remembered_as_a_publish_for_the_throttle() -> None:
    broker, now = Broker(fail=True), [T0]
    live = publisher(broker, now)
    live.forming([bar(final=False)])

    broker.fail = False
    now[0] += SECOND // 10
    live.forming([bar(final=False)])

    assert live.published == 1


def test_a_publisher_with_no_broker_publishes_nothing_and_says_so() -> None:
    live = LivePublisher(None, producer="p", now_ns=lambda: T0)

    live.forming([bar(final=False)])
    live.final(bar(final=True))

    assert live.published == 0 and live.enabled is False


def test_each_series_is_throttled_on_its_own() -> None:
    broker, now = Broker(), [T0]
    live = publisher(broker, now)
    other = bar(final=False).model_copy(update={"symbol": "ETHUSDT"})

    live.forming([bar(final=False)])
    live.forming([other])

    assert len(broker.records) == 2
