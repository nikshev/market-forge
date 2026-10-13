"""What travels between the ingest and the chart (REQ-WP-102)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar
from channelflow.live.messages import (
    TOPIC,
    LiveBar,
    key_for,
    live_bar_from_bar,
    parse_record,
    to_record,
)

pytestmark = pytest.mark.trace("REQ-WP-102")

MINUTE = 60_000_000_000
T0 = 1_788_800_000_000_000_000 // MINUTE * MINUTE


def bar(*, final: bool, close: str = "101", volume: str = "3", open_time: int = T0) -> Bar:
    return Bar(
        venue="bybit",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE,
        open_time_ns=open_time,
        close_time_ns=open_time + MINUTE,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal(close),
        volume_base=Decimal(volume),
        volume_quote=Decimal("300"),
        trade_count=5,
        aggressive_buy_base=Decimal("2"),
        aggressive_sell_base=Decimal("1"),
        delta_base=Decimal("1"),
        vwap=Decimal("100"),
        high_time_ns=open_time,
        low_time_ns=open_time,
        first_trade_id="1",
        last_trade_id="5",
        is_final=final,
    )


def test_the_topic_is_versioned_and_the_key_is_venue_and_symbol() -> None:
    assert TOPIC.endswith(".v1")
    assert key_for("bybit", "BTCUSDT") == "bybit:BTCUSDT"


def test_a_bar_is_carried_as_the_rest_bars_are_with_instants_as_strings() -> None:
    live = live_bar_from_bar(bar(final=False))

    assert live.as_wire() == {
        "venue": "bybit",
        "symbol": "BTCUSDT",
        "open_time_ns": str(T0),
        "close_time_ns": str(T0 + MINUTE),
        "open": "100",
        "high": "102",
        "low": "99",
        "close": "101",
        "volume_base": "3",
        "is_final": False,
    }


def test_a_record_round_trips_field_for_field() -> None:
    original = live_bar_from_bar(bar(final=True))

    record = to_record(original, ingest_time_ns=T0 + 5, producer="ingest-bybit")
    restored = parse_record(record)

    assert record.topic == TOPIC and record.key == "bybit:BTCUSDT"
    assert record.producer == "ingest-bybit"
    assert record.event_time_ns == T0 + MINUTE
    assert record.ingest_time_ns == T0 + 5
    assert restored == original


def test_the_ingest_time_travels_on_the_record_so_the_later_forming_bar_can_win() -> None:
    first = to_record(live_bar_from_bar(bar(final=False)), ingest_time_ns=10, producer="p")
    second = to_record(live_bar_from_bar(bar(final=False)), ingest_time_ns=20, producer="p")

    assert (first.ingest_time_ns, second.ingest_time_ns) == (10, 20)


def test_a_record_that_is_not_a_live_bar_is_refused_not_guessed_at() -> None:
    record = to_record(live_bar_from_bar(bar(final=True)), ingest_time_ns=1, producer="p")
    broken = type(record)(
        topic=record.topic,
        key=record.key,
        payload={"venue": "bybit"},
        event_time_ns=1,
        ingest_time_ns=1,
        producer="p",
    )

    with pytest.raises(ValueError, match="live bar"):
        parse_record(broken)


def test_a_live_bar_is_a_value_two_equal_ones_compare_equal() -> None:
    assert live_bar_from_bar(bar(final=True)) == live_bar_from_bar(bar(final=True))
    assert isinstance(live_bar_from_bar(bar(final=True)), LiveBar)
