"""The API's side: a thirty-minute cache, precedence between forming and final, and the relay loop
(REQ-WP-102)."""

from __future__ import annotations

import pytest

from channelflow.live.messages import live_bar_from_bar, to_record
from channelflow.live.relay import WINDOW_NS, LiveCache, LiveRelay
from channelflow.transport.inprocess import InProcessTransport
from tests.unit.live.test_messages import MINUTE, T0, bar

pytestmark = pytest.mark.trace("REQ-WP-102")


def live(*, final: bool, minute: int = 0, close: str = "101", symbol: str = "BTCUSDT"):
    b = bar(final=final, close=close, open_time=T0 + minute * MINUTE)
    return live_bar_from_bar(b.model_copy(update={"symbol": symbol}))


def test_the_window_is_thirty_minutes() -> None:
    assert WINDOW_NS == 30 * MINUTE


def test_a_first_bar_is_kept_and_forwarded() -> None:
    cache = LiveCache()

    forwarded = cache.apply(live(final=False), ingest_time_ns=1)

    assert forwarded is not None
    assert cache.snapshot("bybit", "BTCUSDT") == [forwarded]


def test_a_later_forming_bar_replaces_an_earlier_one_for_the_same_minute() -> None:
    cache = LiveCache()
    cache.apply(live(final=False, close="101"), ingest_time_ns=1)

    cache.apply(live(final=False, close="105"), ingest_time_ns=2)

    (kept,) = cache.snapshot("bybit", "BTCUSDT")
    assert kept.close == "105"


def test_an_older_forming_bar_arriving_late_is_ignored_and_not_forwarded() -> None:
    cache = LiveCache()
    cache.apply(live(final=False, close="105"), ingest_time_ns=5)

    forwarded = cache.apply(live(final=False, close="101"), ingest_time_ns=2)

    assert forwarded is None
    assert cache.snapshot("bybit", "BTCUSDT")[0].close == "105"


def test_a_final_bar_replaces_a_forming_one() -> None:
    cache = LiveCache()
    cache.apply(live(final=False, close="101"), ingest_time_ns=1)

    forwarded = cache.apply(live(final=True, close="102"), ingest_time_ns=2)

    assert forwarded is not None and forwarded.is_final
    assert cache.snapshot("bybit", "BTCUSDT")[0].close == "102"


def test_a_forming_bar_never_replaces_a_final_one_however_late_it_was_ingested() -> None:
    cache = LiveCache()
    cache.apply(live(final=True, close="102"), ingest_time_ns=1)

    forwarded = cache.apply(live(final=False, close="999"), ingest_time_ns=50)

    assert forwarded is None
    (kept,) = cache.snapshot("bybit", "BTCUSDT")
    assert kept.is_final and kept.close == "102"


def test_a_second_final_bar_for_a_minute_does_not_amend_the_first() -> None:
    cache = LiveCache()
    cache.apply(live(final=True, close="102"), ingest_time_ns=1)

    forwarded = cache.apply(live(final=True, close="777"), ingest_time_ns=9)

    assert forwarded is None
    assert cache.snapshot("bybit", "BTCUSDT")[0].close == "102"


def test_the_snapshot_is_oldest_first_and_per_series() -> None:
    cache = LiveCache()
    cache.apply(live(final=True, minute=2), ingest_time_ns=1)
    cache.apply(live(final=True, minute=0), ingest_time_ns=1)
    cache.apply(live(final=True, minute=1), ingest_time_ns=1)
    cache.apply(live(final=True, minute=0, symbol="ETHUSDT"), ingest_time_ns=1)

    got = cache.snapshot("bybit", "BTCUSDT")

    assert [int(b.open_time_ns) - T0 for b in got] == [0, MINUTE, 2 * MINUTE]
    assert len(cache.snapshot("bybit", "ETHUSDT")) == 1
    assert cache.snapshot("bybit", "SOLUSDT") == []


def test_bars_older_than_the_window_behind_the_newest_are_dropped() -> None:
    cache = LiveCache()
    cache.apply(live(final=True, minute=0), ingest_time_ns=1)
    cache.apply(live(final=True, minute=31), ingest_time_ns=1)

    kept = [int(b.open_time_ns) - T0 for b in cache.snapshot("bybit", "BTCUSDT")]

    assert kept == [31 * MINUTE]


def test_a_bar_exactly_at_the_edge_of_the_window_is_kept() -> None:
    cache = LiveCache()
    cache.apply(live(final=True, minute=0), ingest_time_ns=1)
    cache.apply(live(final=True, minute=30), ingest_time_ns=1)

    assert len(cache.snapshot("bybit", "BTCUSDT")) == 2


def test_the_relay_reads_the_topic_caches_and_forwards_only_what_changed() -> None:
    transport = InProcessTransport()
    from channelflow.live.messages import TOPIC

    publisher = transport.publisher()
    for n, (final, close) in enumerate(
        [(False, "101"), (False, "102"), (True, "103"), (False, "999")]
    ):
        publisher.publish(
            to_record(live(final=final, close=close), ingest_time_ns=n + 1, producer="p")
        )
    sent: list[str] = []
    relay = LiveRelay(transport.consumer([TOPIC]), LiveCache(), lambda b: sent.append(b.close))

    handled = relay.run_once()

    assert handled == 4
    assert sent == ["101", "102", "103"]  # the late forming bar after the final is not forwarded
    assert relay.cache.snapshot("bybit", "BTCUSDT")[0].close == "103"


def test_the_relay_survives_a_record_it_cannot_read_and_counts_it() -> None:
    transport = InProcessTransport()
    from channelflow.live.messages import TOPIC
    from channelflow.transport import Record

    publisher = transport.publisher()
    publisher.publish(
        Record(
            topic=TOPIC,
            key="bybit:BTCUSDT",
            payload={"x": 1},
            event_time_ns=1,
            ingest_time_ns=1,
            producer="p",
        )
    )
    publisher.publish(to_record(live(final=True), ingest_time_ns=2, producer="p"))
    relay = LiveRelay(transport.consumer([TOPIC]), LiveCache(), lambda b: None)

    relay.run_once()

    assert relay.unreadable == 1
    assert len(relay.cache.snapshot("bybit", "BTCUSDT")) == 1
