"""PRD section 28.7's live channel (REQ-API-001, REQ-WP-009)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

SUBSCRIBE = {
    "op": "subscribe",
    "venue": "binance",
    "symbol": "BTCUSDT",
    "timeframe": "15m",
    "channels": ["bars", "signals"],
}


@pytest.mark.trace("REQ-API-001")
def test_the_documented_subscribe_message_is_accepted(client: TestClient) -> None:
    """SC-005, FR-011. PRD section 28.7's message, verbatim."""
    with client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        reply = socket.receive_json()

    assert reply["ok"] is True
    assert reply["subscribed"] == ["bars", "signals"]


@pytest.mark.trace("REQ-API-001")
def test_only_subscribed_channels_are_delivered(client: TestClient) -> None:
    """SC-005, FR-011.

    A subscriber given data it did not ask for is a chart rendering something
    its user did not request.
    """
    with client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        socket.receive_json()

        hub = client.app.state.hub  # type: ignore[attr-defined]
        wanted = hub.recipients(channel="bars", venue="binance", symbol="BTCUSDT", timeframe="15m")
        unwanted = hub.recipients(
            channel="channel", venue="binance", symbol="BTCUSDT", timeframe="15m"
        )

    assert len(wanted) == 1
    assert unwanted == [], "'channel' was not subscribed to"


@pytest.mark.trace("REQ-API-001")
def test_another_symbol_is_not_delivered(client: TestClient) -> None:
    """FR-011. The filter is venue, symbol and timeframe as well as channel."""
    with client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        socket.receive_json()
        hub = client.app.state.hub  # type: ignore[attr-defined]

        assert (
            hub.recipients(channel="bars", venue="binance", symbol="ETHUSDT", timeframe="15m") == []
        )
        assert (
            hub.recipients(channel="bars", venue="bybit", symbol="BTCUSDT", timeframe="15m") == []
        )
        assert (
            hub.recipients(channel="bars", venue="binance", symbol="BTCUSDT", timeframe="1m") == []
        )


@pytest.mark.trace("REQ-API-001")
def test_a_published_update_reaches_the_subscriber(client: TestClient) -> None:
    """FR-011. The whole path, not just the filter.

    `portal.call` runs the coroutine on the app's own event loop, which is
    where the socket lives -- the same loop the server would publish from.
    """
    from functools import partial

    # `client.portal` exists only inside the client's own context: entering it
    # starts the app's event loop, which is where the socket lives and where a
    # real server would publish from.
    with client, client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        socket.receive_json()

        hub = client.app.state.hub  # type: ignore[attr-defined]
        delivered = client.portal.call(  # type: ignore[union-attr]
            partial(
                hub.publish,
                channel="bars",
                venue="binance",
                symbol="BTCUSDT",
                timeframe="15m",
                payload={"close": "112480"},
            )
        )
        assert delivered == 1

        update = socket.receive_json()

    assert update["channel"] == "bars"
    assert update["symbol"] == "BTCUSDT"
    assert update["data"] == {"close": "112480"}


@pytest.mark.trace("REQ-API-001")
def test_an_update_nobody_subscribed_to_reaches_nobody(client: TestClient) -> None:
    """FR-011's other direction: publishing is not broadcasting."""
    from functools import partial

    with client, client.websocket_connect("/ws/market") as socket:
        socket.send_json(SUBSCRIBE)
        socket.receive_json()

        hub = client.app.state.hub  # type: ignore[attr-defined]
        delivered = client.portal.call(  # type: ignore[union-attr]
            partial(
                hub.publish,
                channel="features",
                venue="binance",
                symbol="BTCUSDT",
                timeframe="15m",
                payload={"qi_l1": -0.5},
            )
        )

    assert delivered == 0


@pytest.mark.trace("REQ-API-001")
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("not json at all", "not JSON"),
        ('{"op": "unsubscribe"}', "unsupported op"),
        ('{"op": "subscribe", "venue": "binance"}', "missing field"),
        (
            '{"op": "subscribe", "venue": "b", "symbol": "s", "timeframe": "1m", "channels": []}',
            "non-empty list",
        ),
        (
            '{"op": "subscribe", "venue": "b", "symbol": "s", "timeframe": "1m",'
            ' "channels": ["bras"]}',
            "unknown channel",
        ),
    ],
)
def test_a_malformed_message_is_answered_not_fatal(
    client: TestClient, message: str, expected: str
) -> None:
    """SC-006, FR-012.

    Closing the connection on a bad frame turns a client bug into an outage the
    client cannot diagnose. Note the `"bras"` case: a typo that silently
    subscribed to nothing would look exactly like a quiet market.
    """
    with client.websocket_connect("/ws/market") as socket:
        socket.send_text(message)
        reply = socket.receive_json()

        assert reply["ok"] is False
        assert expected in reply["error"]

        # The connection is still usable, which is the actual requirement.
        socket.send_json(SUBSCRIBE)
        assert socket.receive_json()["ok"] is True
