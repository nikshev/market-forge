"""A reader never ends without saying why, and the session can ask whether it has (REQ-WP-078).

# @trace: REQ-WP-078

OKX's reader swallowed every exception: the daemon opened a URL that answers `HTTP 404`
and the log held nothing but the silence detector's warnings. Binance's transport stored
a failure in `_failure`, which only `connect()` ever read, and ended its thread. A thread
that ends without a word cannot be told from a quiet market, which this repository has
recorded more than once and decided against each time.

The sockets are faked at `websockets.sync.client.connect` for Bybit and OKX and through
`connect_to` for Binance's transport, so these run the real reader code and no network.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from channelflow.connectors.binance.connector import BinanceConnector
from channelflow.connectors.bybit.connector import BybitConnector
from channelflow.connectors.okx.connector import OkxConnector
from channelflow.connectors.websocket import WebsocketTransport, binance_stream_url

SUBSCRIBERS = [("bybit", BybitConnector), ("okx", OkxConnector)]
OKX_ERROR = json.dumps(
    {
        "event": "error",
        "msg": "Subscribe failed, wrong URL or channel:trades,instId:trades.BTC-USDT-SWAP "
        "doesn't exist. Please use the correct URL, channel and parameters referring to "
        "API document.",
        "code": "60018",
        "connId": "b2b0944b",
    }
)


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Messages at WARNING or above from the connectors, whichever logger said them.

    From `channelflow.connectors` only: `caplog` collects every logger, and other tests in
    the suite leave threads that log on their own schedule.
    """
    return [
        r.getMessage()
        for r in caplog.records
        if r.name.startswith("channelflow.connectors") and r.levelno >= logging.WARNING
    ]


def _run_to_the_end(cls, *, open_error=None, recv=None):  # type: ignore[no-untyped-def]
    with patch("websockets.sync.client.connect") as connect:
        if open_error is not None:
            connect.side_effect = open_error
        else:
            ws = MagicMock()
            ws.recv.side_effect = recv
            connect.return_value.__enter__.return_value = ws
        connector = cls(url="wss://test", subscribe_msg="{}")
        connector.connect(("stream",))
        assert connector._thread is not None
        connector._thread.join(timeout=3)
    return connector


# --- Bybit and OKX --------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_a_socket_that_will_not_open_is_a_warning_and_a_dead_reader(
    venue: str, cls: type, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    connector = _run_to_the_end(cls, open_error=OSError("server rejected: HTTP 404"))

    assert connector.alive is False
    said = _warnings(caplog)
    assert any(venue in m and "HTTP 404" in m for m in said), said


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_a_failure_mid_stream_keeps_what_arrived_and_says_why(
    venue: str, cls: type, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    connector = _run_to_the_end(cls, recv=["a frame", ConnectionError("lost the link")])

    assert connector.alive is False
    assert connector.drain_frames() == ["a frame"]
    said = _warnings(caplog)
    assert any(venue in m and "lost the link" in m for m in said), said


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_a_close_from_the_venue_is_logged_with_its_code(
    venue: str, cls: type, caplog: pytest.LogCaptureFixture
) -> None:
    """OKX closes an idle connection with 4004. That close was announced and nothing read it."""
    caplog.set_level(logging.INFO)
    closed = ConnectionClosedError(Close(4004, "No data received in 30s"), None)

    connector = _run_to_the_end(cls, recv=[closed])

    assert connector.alive is False
    said = _warnings(caplog)
    assert any(venue in m and "4004" in m for m in said), said


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_a_reader_that_is_running_is_alive_and_a_close_we_asked_for_is_not_an_error(
    venue: str, cls: type, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    release = threading.Event()

    def block() -> str:
        release.wait(timeout=5)
        raise ConnectionError("socket closed under the reader")

    with patch("websockets.sync.client.connect") as connect:
        ws = MagicMock()
        ws.recv.side_effect = block
        ws.close.side_effect = lambda *a, **k: release.set()
        connect.return_value.__enter__.return_value = ws
        connector = cls(url="wss://test", subscribe_msg="{}")
        connector.connect(("stream",))
        assert connector.alive is True

        connector.close()

    assert connector.alive is False
    assert _warnings(caplog) == [], "a close this process asked for was reported as a failure"


# --- rejections -----------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("venue", "cls", "frame", "quote"),
    [
        ("okx", OkxConnector, OKX_ERROR, "Subscribe failed"),
        (
            "bybit",
            BybitConnector,
            json.dumps(
                {
                    "success": False,
                    "ret_msg": "error:handler not found,topic:publicTrade.NOTASYMBOL",
                    "conn_id": "x",
                    "req_id": "",
                    "op": "subscribe",
                }
            ),
            "handler not found",
        ),
    ],
)
def test_a_refusal_is_queued_for_the_archive_and_warned_with_the_venues_words(
    venue: str, cls: type, frame: str, quote: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    connector = _run_to_the_end(cls, recv=[frame, ConnectionError("end of test")])

    assert connector.drain_frames() == [frame], "the archive must keep what the venue said"
    rejected = [m for m in _warnings(caplog) if "rejected" in m]
    assert len(rejected) == 1 and venue in rejected[0] and quote in rejected[0], rejected


# --- Binance --------------------------------------------------------------------


class _Socket:
    def __init__(self, frames: list[str], error: Exception) -> None:
        self._frames, self._error = list(frames), error

    async def recv(self) -> str:
        if self._frames:
            return self._frames.pop(0)
        await asyncio.sleep(0.1)  # after `connect()` has returned: no race with its check
        raise self._error


class _Connection:
    def __init__(self, socket: _Socket) -> None:
        self._socket = socket

    async def __aenter__(self) -> _Socket:
        return self._socket

    async def __aexit__(self, *exc: object) -> bool:
        return False


@pytest.mark.trace("REQ-WP-078")
def test_binances_transport_logs_a_failure_after_connect_and_stops_being_alive(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`_failure` was stored and read only by `connect()`, on the first connection."""
    caplog.set_level(logging.INFO)
    closed = ConnectionClosedError(Close(1006, "abnormal closure"), None)
    socket = _Socket(["a frame"], closed)
    connector = BinanceConnector(url_for=binance_stream_url)
    connector._transport.connect_to = lambda url, **kw: _Connection(socket)

    connector.connect(("btcusdt@aggTrade",))
    assert connector.alive is True
    assert connector._transport._thread is not None
    connector._transport._thread.join(timeout=3)

    assert connector.alive is False
    assert connector.drain_frames() == ["a frame"]
    said = _warnings(caplog)
    assert any("binance" in m and "1006" in m for m in said), said


@pytest.mark.trace("REQ-WP-078")
def test_a_transport_that_was_never_connected_is_not_alive() -> None:
    assert WebsocketTransport(url_for=binance_stream_url).alive is False


# --- the protocol ---------------------------------------------------------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("cls", [BinanceConnector, BybitConnector, OkxConnector])
def test_every_real_connector_answers_whether_its_reader_is_running(cls: type) -> None:
    """The earlier protocol test asked `hasattr` of a fake, which tests the fake."""
    assert isinstance(getattr(cls, "alive", None), property)


@pytest.mark.trace("REQ-WP-078")
def test_the_protocol_names_alive() -> None:
    from channelflow.connectors.venue import VenueConnector

    assert isinstance(VenueConnector.__dict__.get("alive"), property)


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_alive_is_false_as_soon_as_a_stop_is_asked_for_not_when_the_reader_returns(
    venue: str, cls: type
) -> None:
    """`close()` joins the thread, so after it `alive` is false for the plain reason that
    the thread is gone. The case that matters is the window before that: a stop requested
    and a reader still blocked in `recv`. A session that polled `alive` there and read True
    would not reconnect a connection it had itself just told to stop."""
    release = threading.Event()

    def block() -> str:
        release.wait(timeout=5)
        raise ConnectionError("released")

    with patch("websockets.sync.client.connect") as connect:
        ws = MagicMock()
        ws.recv.side_effect = block
        connect.return_value.__enter__.return_value = ws
        connector = cls(url="wss://test", subscribe_msg="{}")
        connector.connect(("stream",))
        assert connector.alive is True

        connector._stop.set()  # a stop has been asked for; the reader has not returned

        assert connector._thread is not None and connector._thread.is_alive()
        assert connector.alive is False
        release.set()
        connector._thread.join(timeout=3)


# --- found live: a write to the socket the last connection left behind ---------------


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_a_send_after_the_reader_ended_does_not_write_to_the_dead_socket(
    venue: str, cls: type
) -> None:
    """The reader ended; `self._ws` still pointed at the closed socket. The next client
    ping went there and raised `ConnectionClosedError` out of `StreamSession.tick`, and the
    process died. The first send (the subscription) works and every later one raises, as a
    closed socket does."""
    closed = ConnectionClosedError(Close(1011, "keepalive ping timeout"), None)
    with patch("websockets.sync.client.connect") as connect:
        ws = MagicMock()
        ws.send.side_effect = [None, closed, closed]
        ws.recv.side_effect = [ConnectionError("the link went")]
        connect.return_value.__enter__.return_value = ws
        connector = cls(url="wss://test", subscribe_msg="{}")
        connector.connect(("stream",))
        assert connector._thread is not None
        connector._thread.join(timeout=3)

    connector.send("ping")  # must not raise, and must not reach the closed socket

    assert ws.send.call_count == 1, "only the subscription was ever sent on that socket"


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_a_new_connect_forgets_the_previous_socket_before_the_new_one_opens(
    venue: str, cls: type
) -> None:
    """Between `connect()` returning and the new socket opening -- up to ten seconds while a
    venue is unreachable -- the connector must not offer the old socket to `send`."""
    release = threading.Event()

    def opens_slowly(*a: object, **k: object) -> object:
        release.wait(timeout=5)
        raise OSError("never opened")

    connector = cls(url="wss://test", subscribe_msg="{}")
    connector._ws = MagicMock(name="the previous connection's socket")

    with patch("websockets.sync.client.connect", side_effect=opens_slowly):
        connector.connect(("stream",))

        assert connector._ws is None
        connector.send("ping")  # a no-op with no socket, not a write to the old one
        release.set()
        assert connector._thread is not None
        connector._thread.join(timeout=3)


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(("venue", "cls"), SUBSCRIBERS)
def test_an_old_reader_ending_does_not_forget_its_replacements_socket(
    venue: str, cls: type
) -> None:
    """A reconnect starts a new reader while the old one may still be finishing. When the old
    one ends it must clear only its own socket: clearing the new one's would leave the new
    connection alive and unpingable."""
    old_may_end = threading.Event()
    new_may_end = threading.Event()

    def blocking(gate: threading.Event) -> MagicMock:
        ws = MagicMock()

        def recv() -> str:
            gate.wait(5)
            raise ConnectionError("the link went")

        ws.recv.side_effect = recv
        return ws

    old_ws, new_ws = blocking(old_may_end), blocking(new_may_end)
    contexts = [MagicMock(), MagicMock()]
    contexts[0].__enter__.return_value = old_ws
    contexts[1].__enter__.return_value = new_ws

    with patch("websockets.sync.client.connect", side_effect=contexts):
        connector = cls(url="wss://test", subscribe_msg="{}")
        connector.connect(("stream",))
        old_thread = connector._thread
        deadline = time.monotonic() + 3
        while connector._ws is not old_ws and time.monotonic() < deadline:
            time.sleep(0.01)
        assert connector._ws is old_ws

        connector.connect(("stream",))
        while connector._ws is not new_ws and time.monotonic() < deadline:
            time.sleep(0.01)
        assert connector._ws is new_ws

        old_may_end.set()
        assert old_thread is not None
        old_thread.join(timeout=3)
        assert not old_thread.is_alive()

        assert connector._ws is new_ws, "the old reader cleared the new connection's socket"
        new_may_end.set()
        assert connector._thread is not None
        connector._thread.join(timeout=3)
