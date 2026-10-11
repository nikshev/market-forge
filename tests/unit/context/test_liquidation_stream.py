"""A venue's liquidation stream as a collector task (REQ-WP-094, spec 146).

What to connect to was measured, not copied: Binance's futures websocket moved to new paths in 2026
and the legacy one connects and then says nothing -- exactly what a quiet liquidation market looks
like, so a test pins the path that works.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from channelflow.connectors.session import FakeClock
from channelflow.context import liquidations as liq
from channelflow.context.pollers import OkxPoller
from channelflow.context.runtime import Collector, CollectorConfig
from channelflow.context.status import Status
from channelflow.lakehouse import Catalog
from channelflow.tables import liquidations as table
from tests.unit.context.doubles import FakeClient, load
from tests.unit.context.test_runtime import FakePoller, MemorySink
from tests.unit.context.test_streams import MINUTE, FakeConnector

SECOND = 1_000_000_000


@pytest.mark.trace("REQ-WP-094")
def test_binance_uses_the_market_path_of_the_futures_websocket_not_the_legacy_one() -> None:
    spec = liq.stream_spec("binance", ["BTCUSDT"])

    assert spec.url == "wss://fstream.binance.com/market/ws/!forceOrder@arr"
    assert spec.url.startswith("wss://fstream.binance.com/market/ws/")
    assert not spec.url.startswith("wss://fstream.binance.com/ws/")
    assert spec.subscribe_message is None  # the URL is the subscription
    assert spec.streams == ("!forceOrder@arr",)


@pytest.mark.trace("REQ-WP-094")
def test_bybit_subscribes_to_one_topic_per_symbol_on_the_linear_socket() -> None:
    spec = liq.stream_spec("bybit", ["BTCUSDT", "ETHUSDT"])

    assert spec.url == "wss://stream.bybit.com/v5/public/linear"
    assert json.loads(spec.subscribe_message or "") == {
        "op": "subscribe",
        "args": ["allLiquidation.BTCUSDT", "allLiquidation.ETHUSDT"],
    }


@pytest.mark.trace("REQ-WP-094")
def test_okx_subscribes_to_the_swap_liquidation_channel() -> None:
    spec = liq.stream_spec("okx", ["BTC-USDT-SWAP"])

    assert spec.url == "wss://ws.okx.com:8443/ws/v5/public"
    assert json.loads(spec.subscribe_message or "") == {
        "op": "subscribe",
        "args": [{"channel": "liquidation-orders", "instType": "SWAP"}],
    }


@pytest.mark.trace("REQ-WP-094")
def test_an_unknown_venue_has_no_liquidation_stream() -> None:
    with pytest.raises(ValueError, match="kraken"):
        liq.stream_spec("kraken", [])
    with pytest.raises(ValueError, match="kraken"):
        liq.parser_for("kraken", [], {})


def task_for(
    catalog: Catalog,
    venue: str,
    symbols: list[str],
    *,
    contract_values: dict[str, Decimal | None] | None = None,
    start_ns: int = 10 * MINUTE,
) -> tuple[Any, FakeConnector, FakeClock, table.LiquidationSink, list[str]]:
    clock = FakeClock(start_ns)
    connector = FakeConnector()
    sink = table.LiquidationSink(table.table_for(catalog))
    failures: list[str] = []
    task = liq.liquidation_task(
        venue=venue,
        symbols=symbols,
        sink=sink,
        now_ns=clock.now_ns,
        on_failure=failures.append,
        contract_values=contract_values,
        clock=clock,
        connector=connector,
    )
    task.start()
    return task, connector, clock, sink, failures


@pytest.mark.trace("REQ-WP-094")
def test_a_recorded_binance_frame_becomes_a_stored_event_for_a_watched_symbol(
    catalog: Catalog,
) -> None:
    frame = load("ws3_binance_market_forceOrder_all")[0]
    symbol = frame["o"]["s"]
    task, connector, clock, sink, failures = task_for(catalog, "binance", [symbol])
    connector.push(json.dumps(frame))
    clock.advance_ns(SECOND)

    task.step()

    assert sink.pending == 1 and failures == []
    sink.flush()
    events, _ = table.read(table.table_for(catalog))
    (stored,) = events[("binance", symbol)]
    assert stored.meta.ingest_time_ns == clock.now_ns()


@pytest.mark.trace("REQ-WP-094")
def test_a_frame_for_a_symbol_not_watched_is_not_stored(catalog: Catalog) -> None:
    frame = load("ws3_binance_market_forceOrder_all")[0]
    task, connector, _, sink, _ = task_for(catalog, "binance", ["BTCUSDT"])
    connector.push(json.dumps(frame))

    task.step()

    assert sink.pending == 0


@pytest.mark.trace("REQ-WP-094")
def test_a_frame_that_is_not_json_is_counted_and_the_next_is_still_stored(catalog: Catalog) -> None:
    frame = load("ws3_binance_market_forceOrder_all")[0]
    task, connector, _, sink, failures = task_for(catalog, "binance", [frame["o"]["s"]])
    connector.push("<html>")
    connector.push(json.dumps(frame))

    task.step()

    assert len(failures) == 1 and "JSONDecodeError" in failures[0]
    assert sink.pending == 1


@pytest.mark.trace("REQ-WP-094")
def test_okxs_bare_pong_is_neither_stored_nor_counted_as_a_failure(catalog: Catalog) -> None:
    """OKX answers the client's ping with the bare word `pong`: not JSON, and not a fault.

    The first live run counted every one of them as a failed frame, which made a healthy stream
    look like a broken one on its own failure counter."""
    task, connector, _, sink, failures = task_for(catalog, "okx", ["BTC-USDT-SWAP"])
    connector.push("pong")
    connector.push(json.dumps("pong"))  # a JSON string is not a liquidation either

    task.step()

    assert sink.pending == 0 and failures == []


@pytest.mark.trace("REQ-WP-094")
def test_every_recorded_okx_frame_for_a_watched_instrument_is_stored(catalog: Catalog) -> None:
    task, connector, _, sink, failures = task_for(
        catalog, "okx", ["MAGIC-USDT-SWAP"], contract_values={"MAGIC-USDT-SWAP": Decimal("10")}
    )
    for frame in load("ws_okx_liquidation"):
        connector.push(json.dumps(frame))

    task.step()

    assert sink.pending >= 1 and failures == []


@pytest.mark.trace("REQ-WP-094")
def test_okx_with_no_contract_value_refuses_its_events_and_counts_them(catalog: Catalog) -> None:
    task, connector, _, sink, failures = task_for(
        catalog, "okx", ["MAGIC-USDT-SWAP"], contract_values={"MAGIC-USDT-SWAP": None}
    )
    for frame in load("ws_okx_liquidation"):
        connector.push(json.dumps(frame))

    task.step()

    assert sink.pending == 0
    assert failures and all("MAGIC-USDT-SWAP" in f for f in failures)


@pytest.mark.trace("REQ-WP-094")
def test_a_heartbeat_is_stored_for_every_symbol_watched_when_a_minute_is_covered(
    catalog: Catalog,
) -> None:
    task, _, clock, sink, _ = task_for(catalog, "binance", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    clock.advance_ns(MINUTE)

    task.step()

    assert sink.pending == 3
    sink.flush()
    _, beats = table.read(table.table_for(catalog))
    assert beats == {
        ("binance", "BTCUSDT"): [11 * MINUTE],
        ("binance", "ETHUSDT"): [11 * MINUTE],
        ("binance", "SOLUSDT"): [11 * MINUTE],
    }


@pytest.mark.trace("REQ-WP-094")
def test_the_collector_steps_its_streams_and_commits_their_sink_with_the_polls(
    catalog: Catalog,
) -> None:
    task, connector, clock, liq_sink, _ = task_for(catalog, "binance", ["BTCUSDT"])
    status = Status(venue="bybit", poll_interval_s=60, now_ns=clock.now_ns)
    sink = MemorySink()
    collector = Collector(
        config=CollectorConfig(venue="bybit", symbols=("BTCUSDT",), flush_interval_s=3600),
        poller=FakePoller(),
        sink=sink,
        now_ns=clock.now_ns,
        status=status,
        streams=(task,),
        extra_sinks=(liq_sink,),
    )
    clock.advance_ns(MINUTE)

    collector.step()
    assert liq_sink.pending == 1  # the minute's heartbeat

    collector.close()
    assert liq_sink.pending == 0
    assert table.table_for(catalog).read().num_rows == 1
    assert connector.closed


@pytest.mark.trace("REQ-WP-094")
def test_okx_contract_values_are_asked_for_through_the_poller_and_none_when_they_cannot_be(
    client: FakeClient,
) -> None:
    poller = OkxPoller(client, lambda: 1)
    assert poller.contract_value("BTC-USDT-SWAP") == Decimal(
        load("okx_instruments")["data"][0]["ctVal"]
    )

    from channelflow.context.rest import RestFailure

    failing = OkxPoller(
        FakeClient(fail={"/api/v5/public/instruments": RestFailure("i", "HTTP 500")}), lambda: 1
    )
    assert failing.contract_value("BTC-USDT-SWAP") is None


@pytest.mark.trace("REQ-WP-094")
def test_a_liquidation_stream_that_says_nothing_for_ten_minutes_is_not_reconnected(
    catalog: Catalog,
) -> None:
    """Quiet is normal here; the policy's 60 s silence limit would remake the stream each minute."""
    task, connector, clock, _, _ = task_for(catalog, "binance", ["BTCUSDT"])
    for _ in range(10):
        clock.advance_ns(MINUTE)
        task.step()

    assert connector.connects == 1
