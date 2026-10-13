"""The ingest publishes the bars it holds, and a broker never costs it a trade (REQ-WP-102)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from channelflow.live.messages import parse_record
from channelflow.live.publisher import LivePublisher
from channelflow.pipeline.ingest_main import final_and_live
from channelflow.transport import Record
from tests.unit.pipeline.test_ingest import MINUTE_NS, _daemon


@dataclass
class Broker:
    records: list[Record] = field(default_factory=list)
    fail: bool = False

    def publish(self, record: Record) -> None:
        if self.fail:
            raise BufferError("queue full")
        self.records.append(record)


pytestmark = pytest.mark.trace("REQ-WP-102")


def test_a_step_publishes_the_forming_bar_it_is_building(tmp_path: Path) -> None:
    daemon, _, clock = _daemon(tmp_path, timeframe_ns=MINUTE_NS)
    broker = Broker()
    daemon.live = LivePublisher(broker, producer="ingest-binance", now_ns=clock.now_ns)
    daemon.start()

    daemon.step()

    assert broker.records, "the recorded frames contain trades, so a bar is forming"
    published = [parse_record(r) for r in broker.records]
    assert all(bar.is_final is False for bar in published)
    assert {(b.venue, b.symbol) for b in published} == {("binance", "BTCUSDT")}


def test_the_published_forming_bar_is_the_one_the_builder_holds(tmp_path: Path) -> None:
    daemon, _, clock = _daemon(tmp_path, timeframe_ns=MINUTE_NS)
    broker = Broker()
    daemon.live = LivePublisher(broker, producer="p", now_ns=clock.now_ns)
    daemon.start()

    daemon.step()

    held = daemon.builder.forming()
    last = parse_record(broker.records[-1])
    assert (last.open, last.high, last.low, last.close, last.volume_base) == (
        str(held[-1].open),
        str(held[-1].high),
        str(held[-1].low),
        str(held[-1].close),
        str(held[-1].volume_base),
    )


def test_a_broker_that_fails_costs_the_ingest_no_trade(tmp_path: Path) -> None:
    plain, plain_bars, _ = _daemon(tmp_path / "a", timeframe_ns=MINUTE_NS)
    broken, broken_bars, clock = _daemon(tmp_path / "b", timeframe_ns=MINUTE_NS)
    broken.live = LivePublisher(Broker(fail=True), producer="p", now_ns=clock.now_ns)
    plain.start()
    broken.start()

    a, b = plain.step(), broken.step()

    assert (b.frames, b.trades) == (a.frames, a.trades) and b.trades > 0
    assert broken.live.failures > 0
    assert broken.builder.forming() == plain.builder.forming()


def test_a_daemon_without_a_live_feed_is_unchanged(tmp_path: Path) -> None:
    daemon, _, _ = _daemon(tmp_path, timeframe_ns=MINUTE_NS)
    daemon.start()

    assert daemon.step().trades > 0
    assert daemon.live is None


def test_a_final_bar_goes_to_the_table_sink_and_to_the_live_feed() -> None:
    from tests.unit.live.test_messages import bar

    stored: list = []
    broker = Broker()
    live = LivePublisher(broker, producer="p", now_ns=lambda: 1)

    final_and_live(stored.append, live)(bar(final=True))

    assert len(stored) == 1
    assert [parse_record(r).is_final for r in broker.records] == [True]


def test_a_failing_live_feed_does_not_stop_the_bar_reaching_the_table() -> None:
    from tests.unit.live.test_messages import bar

    stored: list = []
    live = LivePublisher(Broker(fail=True), producer="p", now_ns=lambda: 1)

    final_and_live(stored.append, live)(bar(final=True))

    assert len(stored) == 1


def test_the_table_sink_is_written_first_so_the_record_comes_before_the_view() -> None:
    from tests.unit.live.test_messages import bar

    order: list[str] = []

    class Spy:
        def publish(self, record: Record) -> None:
            order.append("view")

    live = LivePublisher(Spy(), producer="p", now_ns=lambda: 1)
    final_and_live(lambda b: order.append("record"), live)(bar(final=True))

    assert order == ["record", "view"]
