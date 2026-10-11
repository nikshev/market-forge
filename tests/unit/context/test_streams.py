"""A websocket stream inside the collector: frames to a handler, a heartbeat only while connected.

REQ-WP-094 and REQ-WP-095 share this. The session's own lifecycle (reconnect, backoff, pings) is
already tested on a fake clock where it lives; what is pinned here is what the collector adds: a bad
frame never stops the stream, and a minute is called covered only if the connection stayed up for
all of it.
"""

from __future__ import annotations

import queue
from dataclasses import replace

import pytest

from channelflow.connectors.session import BINANCE, BYBIT, FakeClock, StreamSession
from channelflow.context.streams import StreamTask, stream_policy

SECOND = 1_000_000_000
MINUTE = 60 * SECOND


class FakeConnector:
    def __init__(self) -> None:
        self._frames: queue.Queue[str] = queue.Queue()
        self.alive_flag = True
        self.connects = 0
        self.closed = False
        self.sent: list[str] = []

    def connect(self, streams: tuple[str, ...]) -> None:
        self.connects += 1
        self.alive_flag = True

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def pong(self) -> None: ...

    def close(self) -> None:
        self.closed = True

    @property
    def frames(self) -> queue.Queue[str]:
        return self._frames

    @property
    def alive(self) -> bool:
        return self.alive_flag

    def drain_frames(self) -> list[str]:
        out: list[str] = []
        while not self._frames.empty():
            out.append(self._frames.get())
        return out

    def push(self, frame: str) -> None:
        self._frames.put(frame)


def build(policy=None, *, start_ns: int = 10 * MINUTE):  # noqa: ANN001, ANN201
    # A quiet stream, as a Binance liquidation stream is. (Bybit and OKX answer a client ping with a
    # frame, so they are never silent in production; a fake connector here sends no pongs.)
    policy = policy or stream_policy("binance", quiet=True)
    clock = FakeClock(start_ns)
    connector = FakeConnector()
    session = StreamSession(streams=("x",), policy=policy, connector=connector, clock=clock)
    handled: list[tuple[str, int]] = []
    beats: list[int] = []
    failures: list[str] = []

    def handler(frame: str, received_ns: int) -> None:
        if frame == "boom":
            raise ValueError("cannot read this")
        handled.append((frame, received_ns))

    task = StreamTask(
        session=session,
        handler=handler,
        heartbeat=beats.append,
        now_ns=clock.now_ns,
        on_failure=failures.append,
    )
    task.start()
    return task, connector, clock, handled, beats, failures


@pytest.mark.trace("REQ-WP-094")
def test_every_frame_reaches_the_handler_with_the_time_it_was_received() -> None:
    task, connector, clock, handled, _, _ = build()
    connector.push("a")
    connector.push("b")
    clock.advance_ns(SECOND)

    task.step()

    assert handled == [("a", clock.now_ns()), ("b", clock.now_ns())]


@pytest.mark.trace("REQ-WP-094")
def test_a_frame_the_handler_cannot_read_is_counted_and_the_next_one_is_still_handled() -> None:
    task, connector, _, handled, _, failures = build()
    for frame in ("a", "boom", "c"):
        connector.push(frame)

    task.step()

    assert [f for f, _ in handled] == ["a", "c"]
    assert len(failures) == 1 and "ValueError" in failures[0]


@pytest.mark.trace("REQ-WP-094")
def test_a_heartbeat_is_written_for_each_minute_the_connection_stayed_up() -> None:
    task, _, clock, _, beats, _ = build(start_ns=10 * MINUTE)  # connected at exactly minute 10
    clock.advance_ns(MINUTE)  # 11:00
    task.step()
    clock.advance_ns(MINUTE)  # 12:00
    task.step()

    assert beats == [11 * MINUTE, 12 * MINUTE]


@pytest.mark.trace("REQ-WP-094")
def test_a_heartbeat_is_written_once_per_minute_however_often_the_task_steps() -> None:
    task, _, clock, _, beats, _ = build(start_ns=10 * MINUTE)
    clock.advance_ns(MINUTE + 5 * SECOND)
    for _ in range(5):
        task.step()
        clock.advance_ns(SECOND)

    assert beats == [11 * MINUTE]


@pytest.mark.trace("REQ-WP-094")
def test_the_minute_in_which_the_connection_was_made_is_not_covered() -> None:
    """Connected at 10:30: events from 10:00 to 10:30 were never ours to see."""
    task, _, clock, _, beats, _ = build(start_ns=10 * MINUTE + 30 * SECOND)
    clock.advance_ns(30 * SECOND)  # 11:00
    task.step()
    assert beats == []

    clock.advance_ns(MINUTE)  # 12:00 -- the whole of 11:00-12:00 was covered
    task.step()
    assert beats == [12 * MINUTE]


@pytest.mark.trace("REQ-WP-094")
def test_a_reconnect_inside_a_minute_uncovers_that_minute() -> None:
    task, connector, clock, _, beats, _ = build(start_ns=10 * MINUTE)
    clock.advance_ns(MINUTE)
    task.step()  # 11:00 covered
    clock.advance_ns(30 * SECOND)
    connector.alive_flag = False
    task.step()  # the session sees the dead reader and reconnects
    assert connector.connects >= 2
    clock.advance_ns(30 * SECOND)  # 12:00
    task.step()

    assert beats == [11 * MINUTE]  # 12:00 is not: the connection was remade at 11:30


@pytest.mark.trace("REQ-WP-094")
def test_a_dead_reader_writes_no_heartbeat() -> None:
    task, connector, clock, _, beats, _ = build(start_ns=10 * MINUTE)
    connector.alive_flag = False
    clock.advance_ns(MINUTE)
    task.step()
    # the session reconnects, which makes the connection new: nothing covers the minute just ended
    assert beats == []


@pytest.mark.trace("REQ-WP-094")
def test_the_silence_limit_is_disabled_for_a_quiet_stream_but_the_keepalive_is_not() -> None:
    quiet = stream_policy("binance", quiet=True)
    assert quiet.max_silence_ns is None
    assert quiet.keepalive == BINANCE.keepalive and quiet.venue == "binance"

    busy = stream_policy("binance", quiet=False)
    assert busy.max_silence_ns == BINANCE.max_silence_ns

    bybit_quiet = stream_policy("bybit", quiet=True)
    assert bybit_quiet.client_ping_interval_ns == BYBIT.client_ping_interval_ns
    assert replace(bybit_quiet, max_silence_ns=BYBIT.max_silence_ns) == BYBIT


@pytest.mark.trace("REQ-WP-094")
def test_a_quiet_stream_is_not_reconnected_for_being_quiet() -> None:
    task, connector, clock, _, beats, _ = build(policy=stream_policy("binance", quiet=True))
    for _ in range(10):
        clock.advance_ns(MINUTE)
        task.step()

    assert connector.connects == 1
    assert len(beats) == 10


@pytest.mark.trace("REQ-WP-094")
def test_an_unknown_venue_has_no_stream_policy() -> None:
    with pytest.raises(ValueError, match="kraken"):
        stream_policy("kraken", quiet=True)


@pytest.mark.trace("REQ-WP-094")
def test_frames_that_keep_arriving_keep_a_busy_streams_silence_limit_from_firing() -> None:
    """The session must hear of each frame, or its silence limit reconnects a healthy feed."""
    task, connector, clock, _, _, _ = build(policy=stream_policy("binance", quiet=False))
    for _ in range(6):
        clock.advance_ns(30 * SECOND)
        connector.push("data")
        task.step()

    assert connector.connects == 1  # three minutes, never silent for 60 s


@pytest.mark.trace("REQ-WP-094")
def test_a_dead_reader_writes_no_heartbeat_while_the_session_is_still_throttled() -> None:
    """The session throttles reconnects to the venue's connect limit; in that gap the old connection
    is old enough to cover the minute, and dead."""
    slow = replace(
        stream_policy("binance", quiet=True),
        min_connect_interval_ns=30 * MINUTE,
        max_connect_backoff_ns=60 * MINUTE,
    )
    task, connector, clock, _, beats, _ = build(policy=slow, start_ns=10 * MINUTE)
    clock.advance_ns(30 * SECOND)
    connector.alive_flag = False
    clock.advance_ns(30 * SECOND)  # 11:00

    task.step()

    assert connector.connects == 1  # the reconnect was throttled
    assert beats == []


@pytest.mark.trace("REQ-WP-095")
def test_the_tick_callback_runs_on_every_step_with_the_time_so_silent_minutes_can_close() -> None:
    clock = FakeClock(10 * MINUTE)
    connector = FakeConnector()
    session = StreamSession(
        streams=("x",),
        policy=stream_policy("binance", quiet=True),
        connector=connector,
        clock=clock,
    )
    ticks: list[int] = []
    task = StreamTask(
        session=session,
        handler=lambda frame, at: None,
        heartbeat=lambda at: None,
        now_ns=clock.now_ns,
        on_failure=lambda message: None,
        tick=ticks.append,
    )
    task.start()
    clock.advance_ns(SECOND)
    task.step()
    clock.advance_ns(SECOND)
    task.step()

    assert ticks == [10 * MINUTE + SECOND, 10 * MINUTE + 2 * SECOND]


@pytest.mark.trace("REQ-WP-095")
def test_the_reconnect_callback_runs_once_for_each_new_connection_and_not_for_the_first() -> None:
    clock = FakeClock(10 * MINUTE)
    connector = FakeConnector()
    session = StreamSession(
        streams=("x",),
        policy=stream_policy("binance", quiet=True),
        connector=connector,
        clock=clock,
    )
    reconnects: list[int] = []
    task = StreamTask(
        session=session,
        handler=lambda frame, at: None,
        heartbeat=lambda at: None,
        now_ns=clock.now_ns,
        on_failure=lambda message: None,
        on_reconnect=lambda: reconnects.append(clock.now_ns()),
    )
    task.start()
    clock.advance_ns(5 * SECOND)
    task.step()
    assert reconnects == []  # the first connection is not a reconnect

    connector.alive_flag = False
    clock.advance_ns(5 * SECOND)
    task.step()
    clock.advance_ns(5 * SECOND)
    task.step()

    assert reconnects == [10 * MINUTE + 10 * SECOND]
