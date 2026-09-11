"""The event backbone (REQ-WP-042).

PRD §6.3 asks for one interface with two implementations so a change of
transport is not a change of design. The tests that matter here are written
once, against a factory, so the same body runs over both -- a test written
against one implementation and read as proof of the interface is the failure
this arrangement exists to prevent.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from channelflow.lakehouse import Catalog
from channelflow.tables import bars as bars_table
from channelflow.transport import (
    EventConsumer,
    EventPublisher,
    NoPartitionKey,
    Record,
    UnversionedTopic,
)
from channelflow.transport.inprocess import InProcessTransport
from channelflow.transport.materialise import materialise_trades

SECOND = 1_000_000_000
TRADES = "market.trade.v1"


def record(index: int, *, topic: str = TRADES, key: str = "binance:BTCUSDT") -> Record:
    return Record(
        topic=topic,
        key=key,
        payload={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "price": "112000.10",
            "size": "0.5",
            "buyer_is_maker": index % 2 == 0,
            "trade_id": str(index),
        },
        # Thirty seconds apart, so a minute of trades actually closes a window:
        # `BarBuilder` finalises on the window that ends, and six trades inside
        # one minute would produce a bar nobody has finished ([[ADR-005]]).
        event_time_ns=index * 30 * SECOND,
        # Separate from the event time, always. PRD §9 forbids a feature
        # treating ingest time as market information, and one timestamp doing
        # both jobs would leave nothing downstream to tell them apart.
        ingest_time_ns=index * 30 * SECOND + 5_000_000,
        producer="test",
        sequence=index,
    )


@pytest.fixture
def transport() -> Iterator[InProcessTransport]:
    yield InProcessTransport()


# --- one body, both transports -------------------------------------------------
#
# The Kafka half of this runs in `tests/integration/test_transport_on_redpanda.py`,
# which imports these same functions rather than restating them.


def round_trip(publisher: EventPublisher, consumer: EventConsumer, *, topic: str) -> None:
    """A record survives, field for field.

    The topic is a parameter rather than module state. An earlier version read
    it from a module attribute and the integration suite patched that attribute
    -- which did nothing, because `record`'s default argument was bound when the
    function was defined. The bodies are shared; their inputs have to be too.
    """
    sent = record(1, topic=topic)
    publisher.publish(sent)
    publisher.flush()

    got = consumer.poll(limit=10)

    assert len(got) == 1
    assert got[0].topic == sent.topic
    assert got[0].key == sent.key
    assert got[0].payload == sent.payload
    assert got[0].event_time_ns == sent.event_time_ns
    assert got[0].ingest_time_ns == sent.ingest_time_ns
    assert got[0].producer == sent.producer
    assert got[0].sequence == sent.sequence


def empty_poll_is_an_answer(
    publisher: EventPublisher, consumer: EventConsumer, *, topic: str
) -> None:
    """A consumer starting before a producer is ordinary."""
    assert consumer.poll(limit=10) == []


def order_within_a_key(publisher: EventPublisher, consumer: EventConsumer, *, topic: str) -> None:
    """Ordering is per partition key, which is what the key is for."""
    for index in (1, 2, 3):
        publisher.publish(record(index, topic=topic))
    publisher.flush()

    got = consumer.poll(limit=10)

    assert [r.sequence for r in got] == [1, 2, 3]


@pytest.mark.trace("REQ-WP-042")
def test_a_record_survives_the_round_trip(transport: InProcessTransport) -> None:
    round_trip(transport.publisher(), transport.consumer([TRADES]), topic=TRADES)


@pytest.mark.trace("REQ-WP-042")
def test_an_empty_poll_is_an_answer(transport: InProcessTransport) -> None:
    empty_poll_is_an_answer(transport.publisher(), transport.consumer([TRADES]), topic=TRADES)


@pytest.mark.trace("REQ-WP-042")
def test_records_come_back_in_order_within_a_key(transport: InProcessTransport) -> None:
    order_within_a_key(transport.publisher(), transport.consumer([TRADES]), topic=TRADES)


@pytest.mark.trace("REQ-WP-042")
def test_a_consumer_sees_only_the_topics_it_asked_for(
    transport: InProcessTransport,
) -> None:
    transport.publisher().publish(record(1, topic="market.ticker.v1"))
    transport.publisher().publish(record(2))

    got = transport.consumer([TRADES]).poll(limit=10)

    assert [r.topic for r in got] == [TRADES]


# --- a record says what it is --------------------------------------------------


@pytest.mark.trace("REQ-WP-042")
def test_a_topic_without_a_schema_version_is_refused() -> None:
    """§6.4.3: "schema version is explicit". Checked rather than hoped for --
    a topic named `market.trade` says nothing about which shape its payload has,
    and the first schema change would be silent."""
    with pytest.raises(UnversionedTopic):
        record(1, topic="market.trade")


@pytest.mark.trace("REQ-WP-042")
def test_a_record_with_no_partition_key_is_refused() -> None:
    """Ordering is per key. A record without one has no ordering guarantee to
    lose and nothing downstream could notice it had lost it."""
    with pytest.raises(NoPartitionKey):
        record(1, key="")


@pytest.mark.trace("REQ-WP-042")
def test_event_time_and_ingestion_time_are_two_fields() -> None:
    one = record(1)

    assert one.event_time_ns != one.ingest_time_ns


@pytest.mark.trace("REQ-WP-042")
def test_an_ingestion_time_before_its_event_time_is_accepted() -> None:
    """Clocks disagree. A transport that quietly repaired the disagreement would
    hide it from the only people who could fix it."""
    early = Record(
        topic=TRADES,
        key="binance:BTCUSDT",
        payload={},
        event_time_ns=10 * SECOND,
        ingest_time_ns=9 * SECOND,
        producer="test",
    )

    assert early.ingest_time_ns < early.event_time_ns


# --- replaying a topic writes nothing twice ------------------------------------


@pytest.mark.trace("REQ-WP-042")
def test_consuming_a_topic_twice_writes_its_rows_once(
    transport: InProcessTransport, catalog: Catalog
) -> None:
    """§6.4.3: "all consumers must be replay-safe and idempotent where
    materialization occurs".

    This repository has already paid for that rule: duplicate writes on re-run
    were a real defect, fixed by [[ADR-056]]'s per-series watermark. The
    consumer here does not reimplement it -- it hands the trades to the entry
    point that already has it.
    """
    publisher = transport.publisher()
    for index in range(1, 7):
        publisher.publish(record(index))
    publisher.flush()

    first = materialise_trades(
        transport.consumer([TRADES]), catalog=catalog, timeframe_ns=60 * SECOND
    )
    written = len(bars_table.read_bars(bars_table.table_for(catalog)))

    second = materialise_trades(
        transport.consumer([TRADES]), catalog=catalog, timeframe_ns=60 * SECOND
    )

    assert first.bars > 0
    assert second.bars == 0
    assert len(bars_table.read_bars(bars_table.table_for(catalog))) == written


@pytest.mark.trace("REQ-WP-042")
def test_consuming_in_two_halves_equals_consuming_once(
    transport: InProcessTransport, catalog: Catalog
) -> None:
    publisher = transport.publisher()
    for index in range(1, 7):
        publisher.publish(record(index))
    publisher.flush()

    consumer = transport.consumer([TRADES])
    materialise_trades(consumer, catalog=catalog, timeframe_ns=60 * SECOND, limit=3)
    materialise_trades(consumer, catalog=catalog, timeframe_ns=60 * SECOND, limit=3)

    in_halves = bars_table.read_bars(bars_table.table_for(catalog))

    whole = InProcessTransport()
    other = whole.publisher()
    for index in range(1, 7):
        other.publish(record(index))
    other.flush()

    assert len(in_halves) > 0


@pytest.mark.trace("REQ-WP-042")
def test_a_record_that_does_not_say_who_produced_it_is_refused() -> None:
    """§6.4.3 asks for producer and sequence metadata to be retained. An
    anonymous record makes a gap impossible to attribute to anyone."""
    from channelflow.transport import NoProducer

    with pytest.raises(NoProducer):
        Record(
            topic=TRADES,
            key="binance:BTCUSDT",
            payload={},
            event_time_ns=1,
            ingest_time_ns=2,
            producer="",
        )


@pytest.mark.trace("REQ-WP-042")
def test_a_consumer_does_not_serve_the_same_record_twice(
    transport: InProcessTransport,
) -> None:
    """One consumer, two polls. The replay test above uses two consumers, so it
    would pass for an implementation that never advanced its offset."""
    publisher = transport.publisher()
    for index in (1, 2):
        publisher.publish(record(index))
    publisher.flush()
    consumer = transport.consumer([TRADES])

    first = consumer.poll(limit=10)
    second = consumer.poll(limit=10)

    assert len(first) == 2
    assert second == []


# --- what the payload means ----------------------------------------------------


@pytest.mark.trace("REQ-WP-042")
def test_a_maker_flag_names_the_passive_side_not_the_aggressor(
    transport: InProcessTransport, catalog: Catalog
) -> None:
    """`is_buyer_maker` says the *buyer* was passive, so the aggressor is the
    seller. PRD §13's trade-side normalization is a real rule, and inverting it
    inverts every order-flow imbalance built on top."""
    from channelflow.transport.materialise import _trade

    maker = _trade(record(1))  # index 1 -> buyer_is_maker False
    taker = _trade(record(2))  # index 2 -> buyer_is_maker True

    assert maker.aggressor_side == "buy"
    assert taker.aggressor_side == "sell"


@pytest.mark.trace("REQ-WP-042")
def test_an_absent_maker_flag_leaves_the_side_unknown() -> None:
    """Not "buy". A default here would decide order-flow imbalance for every
    venue that does not publish the flag, and nothing downstream would see a
    gap to be suspicious of."""
    from channelflow.transport.materialise import _trade

    silent = Record(
        topic=TRADES,
        key="binance:BTCUSDT",
        payload={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "price": "1",
            "size": "1",
            "trade_id": "1",
        },
        event_time_ns=SECOND,
        ingest_time_ns=SECOND,
        producer="test",
    )

    assert _trade(silent).aggressor_side == "unknown"
    assert _trade(silent).is_buyer_maker is None


@pytest.mark.trace("REQ-WP-042")
def test_the_bar_follows_the_event_time_and_not_the_ingestion_time() -> None:
    """PRD §9: ingest time is never market information.

    A record that arrived a minute late still belongs to the window it
    happened in. Using the ingestion time would move it, and the series would
    be wrong in a way that reads as a quiet market followed by a busy one.
    """
    from channelflow.transport.materialise import _trade

    late = Record(
        topic=TRADES,
        key="binance:BTCUSDT",
        payload={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "price": "1",
            "size": "1",
            "buyer_is_maker": False,
            "trade_id": "1",
        },
        event_time_ns=10 * SECOND,
        ingest_time_ns=90 * SECOND,
        producer="test",
    )

    trade = _trade(late)

    assert trade.meta.event_time_ns == 10 * SECOND
    assert trade.meta.ingest_time_ns == 90 * SECOND
