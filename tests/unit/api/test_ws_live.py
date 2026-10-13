"""The live bars on `/ws/market`: a snapshot first, then updates, and only to who asked
(REQ-WP-102)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from channelflow.api.app import create_app
from channelflow.api.repositories import Repository
from channelflow.live.messages import live_bar_from_bar
from channelflow.live.relay import LiveCache
from tests.unit.live.test_messages import MINUTE, T0, bar

pytestmark = pytest.mark.trace("REQ-WP-102")

SUBSCRIBE = {
    "op": "subscribe",
    "venue": "bybit",
    "symbol": "BTCUSDT",
    "timeframe": "1m",
    "channels": ["bars"],
}


def cached(cache: LiveCache, *, minute: int, final: bool = True, close: str = "101") -> None:
    cache.apply(
        live_bar_from_bar(bar(final=final, close=close, open_time=T0 + minute * MINUTE)),
        ingest_time_ns=minute + 1,
    )


@pytest.fixture
def cache() -> LiveCache:
    return LiveCache()


@pytest.fixture
def live_client(repository: Repository, cache: LiveCache) -> TestClient:
    return TestClient(create_app(repository=repository, live_cache=cache))


def test_a_one_minute_bars_subscription_is_acknowledged_as_live_and_gets_the_cache_first(
    live_client: TestClient, cache: LiveCache
) -> None:
    cached(cache, minute=0)
    cached(cache, minute=1, final=False, close="105")

    with live_client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        ack = socket.receive_json()
        snapshot = socket.receive_json()

    assert ack["ok"] is True and ack["live"] is True
    assert snapshot["channel"] == "bars" and snapshot["timeframe"] == "1m"
    bars = snapshot["data"]["snapshot"]
    assert [b["open_time_ns"] for b in bars] == [str(T0), str(T0 + MINUTE)]
    assert [b["is_final"] for b in bars] == [True, False]


def test_an_empty_cache_still_sends_an_empty_snapshot_so_the_page_knows_it_has_heard_everything(
    live_client: TestClient,
) -> None:
    with live_client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        socket.receive_json()
        snapshot = socket.receive_json()

    assert snapshot["data"]["snapshot"] == []


def test_a_subscription_at_another_timeframe_is_acknowledged_as_not_live_and_gets_no_snapshot(
    live_client: TestClient, cache: LiveCache
) -> None:
    cached(cache, minute=0)

    with live_client.websocket_connect("/ws/market") as socket:
        socket.send_json({**SUBSCRIBE, "timeframe": "15m"})
        ack = socket.receive_json()
        socket.send_json({**SUBSCRIBE, "timeframe": "15m", "symbol": "ETHUSDT"})
        second = socket.receive_json()

    assert ack["live"] is False
    assert second["ok"] is True  # the next message is an acknowledgement, not a snapshot


def test_an_app_with_no_live_feed_says_so(client: TestClient) -> None:
    with client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        ack = socket.receive_json()

    assert ack["ok"] is True and ack["live"] is False


def test_a_subscriber_to_other_signals_only_gets_no_snapshot(
    live_client: TestClient, cache: LiveCache
) -> None:
    cached(cache, minute=0)

    with live_client.websocket_connect("/ws/market") as socket:
        socket.send_json({**SUBSCRIBE, "channels": ["signals"]})
        ack = socket.receive_json()
        socket.send_json({**SUBSCRIBE, "channels": ["signals"], "symbol": "X"})
        second = socket.receive_json()

    assert ack["live"] is False
    assert second["ok"] is True


def test_a_published_bar_reaches_the_subscriber_of_that_series_and_not_another(
    repository: Repository, cache: LiveCache
) -> None:
    app = create_app(repository=repository, live_cache=cache)
    hub = app.state.hub
    with TestClient(app) as client:
        with (
            client.websocket_connect("/ws/market") as mine,
            client.websocket_connect("/ws/market") as theirs,
        ):
            mine.send_json(SUBSCRIBE)
            mine.receive_json()
            mine.receive_json()
            theirs.send_json({**SUBSCRIBE, "symbol": "ETHUSDT"})
            theirs.receive_json()
            theirs.receive_json()

            delivered = client.portal.call(  # type: ignore[union-attr]
                hub.publish_bar, live_bar_from_bar(bar(final=False, close="123"))
            )
            update = mine.receive_json()

    assert delivered == 1
    assert update["channel"] == "bars" and update["timeframe"] == "1m"
    assert update["data"]["bar"]["close"] == "123" and update["data"]["bar"]["is_final"] is False


def test_a_socket_that_has_gone_away_does_not_stop_the_others(
    repository: Repository, cache: LiveCache
) -> None:
    app = create_app(repository=repository, live_cache=cache)
    hub = app.state.hub

    class Dead:
        async def send_json(self, _: object) -> None:
            raise RuntimeError("connection closed")

    import json

    from channelflow.api.ws import parse_subscribe

    hub.subscribe(Dead(), parse_subscribe(json.dumps(SUBSCRIBE)))
    with TestClient(app) as client, client.websocket_connect("/ws/market") as live:
        live.send_json(SUBSCRIBE)
        live.receive_json()
        live.receive_json()

        portal = client.portal
        assert portal is not None
        delivered = portal.call(hub.publish_bar, live_bar_from_bar(bar(final=True)))
        got = live.receive_json()

    assert delivered == 1 and got["data"]["bar"]["is_final"] is True


def test_a_record_on_the_topic_reaches_a_subscriber_through_the_relay(
    repository: Repository,
) -> None:
    """The whole path inside the API: topic -> relay thread -> cache -> hub -> socket."""
    import time

    from channelflow.api.live import attach_live
    from channelflow.live.messages import TOPIC_FINAL, TOPIC_FORMING, to_record
    from channelflow.transport.inprocess import InProcessTransport

    transport = InProcessTransport()
    cache = LiveCache()
    app = create_app(repository=repository, live_cache=cache)
    attach_live(app, cache, lambda: (transport.consumer([TOPIC_FINAL, TOPIC_FORMING]), None))

    with TestClient(app) as client, client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        socket.receive_json()
        assert socket.receive_json()["data"]["snapshot"] == []
        # What is on the topic when the API starts is history; a bar published after it is news.
        deadline = time.monotonic() + 10
        while getattr(app.state, "live_relay", None) is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert app.state.live_relay.caught_up.wait(10)

        transport.publisher().publish(
            to_record(
                live_bar_from_bar(bar(final=False, close="321")), ingest_time_ns=1, producer="p"
            )
        )
        update = socket.receive_json()
        deadline = time.monotonic() + 5

    assert update["data"]["bar"]["close"] == "321"
    assert deadline  # received within the receive's own wait; no polling loop in the test
    assert [b.close for b in cache.snapshot("bybit", "BTCUSDT")] == ["321"]


def test_an_api_whose_broker_is_unreachable_still_serves_and_says_the_feed_is_empty(
    repository: Repository,
) -> None:
    from channelflow.api.live import attach_live

    def no_broker():  # type: ignore[no-untyped-def]
        raise RuntimeError("broker unreachable")

    cache = LiveCache()
    app = create_app(repository=repository, live_cache=cache)
    attach_live(app, cache, no_broker)

    with TestClient(app) as client:
        assert client.get("/readyz").status_code in (200, 503)
        with client.websocket_connect("/ws/market") as socket:
            socket.send_json(SUBSCRIBE)
            socket.receive_json()
            assert socket.receive_json()["data"]["snapshot"] == []
