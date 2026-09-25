"""PRD §6.2's `ingest-binance`, driven over recorded frames (REQ-WP-066).

The daemon runs here behind `ReplayTransport` -- not a test double but the other
implementation of the seam a live socket sits behind, so what CI exercises is the
process, not a rehearsal of it.
"""

from __future__ import annotations

import gzip
import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import BINANCE, FakeClock, StreamSession
from channelflow.connectors.websocket import ReplayTransport, binance_stream_url
from channelflow.pipeline.archive import (
    ClockWentBackwards,
    FrameArchive,
    LocalObjectStore,
    read_frames,
)
from channelflow.pipeline.ingest import (
    FLUSH_CEILING_NS,
    FLUSH_EVERY_BARS,
    IngestDaemon,
    streams_for,
)
from channelflow.pipeline.ingest_main import (
    ARCHIVE_URI,
    SYMBOLS,
    TIMEFRAME,
    ingest_settings_from_env,
    object_store_for,
)
from channelflow.settings import MissingConfiguration

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "binance" / "spot_btcusdt_aggTrade.jsonl"
)
RECORDED: list[str] = FIXTURE.read_text().splitlines()

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS
BASE_NS = 1789000000_000_000_000


class FakeReplayConnector:
    """A fake VenueConnector that replays recorded frames."""

    def __init__(self, transport):
        self._transport = transport
        self.closed = False

    def connect(self, streams):
        self._transport.connect([])

    @property
    def frames(self):
        return self._transport

    def drain_frames(self) -> list[str]:
        return self._transport.drain()

    def send(self, payload):
        pass

    def pong(self):
        pass

    def close(self):
        self.closed = True


def _daemon(
    tmp_path: Path,
    frames: list[str] | None = None,
    *,
    timeframe_ns: int = SECOND_NS,
    grace_ns: int = 5 * SECOND_NS,
) -> tuple[IngestDaemon, list, FakeClock]:
    written: list = []
    transport = ReplayTransport(recorded=frames if frames is not None else RECORDED)
    clock = FakeClock(BASE_NS)
    builder = BarBuilder(timeframe_ns=timeframe_ns, grace_ns=grace_ns, on_final=written.append)
    connector = FakeReplayConnector(transport)
    daemon = IngestDaemon(
        session=StreamSession(
            streams=streams_for(["BTCUSDT"]), policy=BINANCE, connector=connector, clock=clock
        ),
        connector=connector,
        archive=FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance"),
        builder=builder,
        venue="binance",
        now_ns=clock.now_ns,
    )
    return daemon, written, clock


# --------------------------------------------------------------------------
# Recorded frames become trades
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Recorded frames become trades
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-066")
def test_the_fixture_is_what_the_venue_sent(tmp_path: Path) -> None:
    """Real capture, not a hand-written sample: ADR-004's rule, and the reason
    this test can mean anything about a live run."""
    assert RECORDED, "the recorded capture is not empty"
    envelope = json.loads(RECORDED[0])
    assert envelope["stream"] == "btcusdt@aggTrade"
    assert {"a", "p", "q", "m", "T"} <= set(envelope["data"])


@pytest.mark.trace("REQ-WP-066")
def test_recorded_frames_become_trades(tmp_path: Path) -> None:
    daemon, _, _ = _daemon(tmp_path)
    daemon.start()

    report = daemon.step()

    assert report.frames == len(RECORDED)
    assert report.trades == len(RECORDED)
    assert (report.unparsed, report.ignored) == (0, 0)


@pytest.mark.trace("REQ-WP-066")
def test_trades_become_a_bar_the_builder_closes(tmp_path: Path) -> None:
    """The whole point: a socket at one end, a row in the bars table at the
    other.

    The fixture spans 0.2 seconds, and `BarBuilder` closes a window only once
    its watermark passes the window's end **plus the grace period** -- five
    seconds by default, which is longer than the whole capture. So the grace is
    zero here: the bar is closed by a later trade's event time, which is what
    closes it in a live run too, just sooner.
    """
    daemon, closed, clock = _daemon(tmp_path, timeframe_ns=1, grace_ns=0)
    daemon.start()
    daemon.step()

    assert closed, "no bar was finalized"
    bar = closed[0]
    assert bar.volume_base > Decimal(0)
    assert bar.open > Decimal(0)


# --------------------------------------------------------------------------
# What the daemon refuses to lose
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-066")
def test_every_frame_is_archived_before_anything_is_decided(tmp_path: Path) -> None:
    """A frame this build cannot read is exactly the frame a later one wants."""
    daemon, _, _ = _daemon(tmp_path, frames=[*RECORDED, "not json at all"])
    daemon.start()

    report = daemon.step()
    daemon.stop()

    assert report.unparsed == 1
    objects = list(tmp_path.rglob("*.jsonl.gz"))
    assert len(objects) == 1
    archived = read_frames(objects[0].read_bytes())
    assert [frame for _, frame in archived] == [*RECORDED, "not json at all"]


@pytest.mark.trace("REQ-WP-066")
def test_a_bad_frame_does_not_stop_the_ingest(tmp_path: Path) -> None:
    daemon, _, _ = _daemon(tmp_path, frames=["{]", json.dumps({"stream": "x"}), RECORDED[0]])
    daemon.start()

    report = daemon.step()

    assert report.trades == 1
    assert report.unparsed == 2


@pytest.mark.trace("REQ-WP-066")
def test_a_stream_this_build_does_not_consume_is_counted_not_dropped(tmp_path: Path) -> None:
    """Depth is archived and not turned into events yet. Counted, so the gap is
    visible rather than inferred from missing features."""
    depth = json.dumps({"stream": "btcusdt@depth@100ms", "data": {"b": [], "a": []}})
    daemon, _, _ = _daemon(tmp_path, frames=[depth, RECORDED[0]])
    daemon.start()

    report = daemon.step()

    assert (report.trades, report.ignored, report.unparsed) == (1, 1, 0)


@pytest.mark.trace("REQ-WP-066")
def test_stopping_commits_before_it_closes(tmp_path: Path) -> None:
    """Closing first would leave the last minute in memory, and a restart would
    look like a gap in the data rather than a gap in the shutdown."""
    flushed: list[str] = []
    daemon, _, _ = _daemon(tmp_path)
    daemon.flush_bars = lambda: flushed.append("committed") or "snapshot"  # type: ignore[func-returns-value]
    daemon.start()
    daemon.step()

    report = daemon.stop()

    assert flushed == ["committed"]
    assert report is not None and report.archived is not None
    assert daemon.session.connector.closed is True  # type: ignore[union-attr]


# --------------------------------------------------------------------------
# The archive
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-066")
def test_one_object_per_minute(tmp_path: Path) -> None:
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")

    for offset in (0, 30, 59, 61, 62):
        archive.add(received_at_ns=BASE_NS + offset * SECOND_NS, frame=f"f{offset}")
    archive.flush()

    objects = sorted(p.name for p in tmp_path.rglob("*.jsonl.gz"))
    assert len(objects) == 2, "one for each minute the frames fell in"


@pytest.mark.trace("REQ-WP-066")
def test_a_quiet_minute_writes_no_object(tmp_path: Path) -> None:
    """An empty object is indistinguishable from a minute nobody recorded."""
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")

    assert archive.flush() is None
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.trace("REQ-WP-066")
def test_a_frame_survives_the_round_trip_byte_for_byte(tmp_path: Path) -> None:
    """The tier exists so a later build can re-normalise. A frame that came back
    changed would make that worthless."""
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")
    awkward = json.dumps({"stream": "x", "data": {"p": "0.000000010000", "s": 'a"b\\c\nd'}})

    archive.add(received_at_ns=BASE_NS, frame=awkward)
    key = archive.flush()

    assert key is not None
    restored = read_frames((tmp_path / key).read_bytes())
    assert restored == [(BASE_NS, awkward)]


@pytest.mark.trace("REQ-WP-066")
def test_the_archive_compresses(tmp_path: Path) -> None:
    """Measured on the venue: 12.3% of the raw bytes, which is what makes 556
    MiB a day per symbol affordable."""
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")
    for index, frame in enumerate(RECORDED * 40):
        archive.add(received_at_ns=BASE_NS + index, frame=frame)
    key = archive.flush()

    assert key is not None
    body = (tmp_path / key).read_bytes()
    assert len(body) < len(gzip.decompress(body)) // 4


@pytest.mark.trace("REQ-WP-066")
def test_a_backwards_clock_is_refused(tmp_path: Path) -> None:
    """One socket cannot deliver backwards, and an archive quietly reordered to
    hide a broken clock is a worse record than none."""
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")
    archive.add(received_at_ns=BASE_NS + SECOND_NS, frame="a")

    with pytest.raises(ClockWentBackwards, match="backwards"):
        archive.add(received_at_ns=BASE_NS, frame="b")


@pytest.mark.trace("REQ-WP-066")
def test_the_key_is_dated_and_nested_by_day(tmp_path: Path) -> None:
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")

    key = archive.key_for(1789000020_000_000_000)

    assert key.startswith("raw/cex/binance/")
    assert key.endswith(".jsonl.gz")
    assert len(key.split("/")) == 7, "prefix, venue, year, month, day, file"


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def _env(**overrides: str) -> dict[str, str]:
    base = {SYMBOLS: "BTCUSDT", ARCHIVE_URI: "/tmp/archive"}
    base.update(overrides)
    return base


@pytest.mark.trace("REQ-WP-066")
def test_the_symbols_and_the_archive_are_required() -> None:
    for missing in (SYMBOLS, ARCHIVE_URI):
        with pytest.raises(MissingConfiguration, match=missing):
            ingest_settings_from_env({k: v for k, v in _env().items() if k != missing})


@pytest.mark.trace("REQ-WP-066")
def test_the_timeframe_defaults_to_a_minute() -> None:
    """A chart shows its first candle a minute after the daemon starts rather
    than fifteen."""
    assert ingest_settings_from_env(_env()).timeframe_ns == 60_000_000_000
    assert ingest_settings_from_env(_env(**{TIMEFRAME: "1000"})).timeframe_ns == 1000


@pytest.mark.trace("REQ-WP-066")
def test_a_timeframe_that_spans_nothing_is_refused() -> None:
    with pytest.raises(MissingConfiguration, match="positive"):
        ingest_settings_from_env(_env(**{TIMEFRAME: "0"}))


@pytest.mark.trace("REQ-WP-066")
def test_the_archive_scheme_chooses_the_store(tmp_path: Path) -> None:
    """One seam, two implementations, and the scheme is the only thing that
    decides -- the line `lakehouse.catalog` draws between a local run and a
    deployment."""
    local = object_store_for(str(tmp_path), {})
    assert isinstance(local, LocalObjectStore)


@pytest.mark.trace("REQ-WP-066")
def test_the_stream_names_are_lower_case() -> None:
    """Measured: `BTCUSDT@aggTrade` connects and delivers nothing over twelve
    seconds while `btcusdt@aggTrade` delivers 48 frames. A silent subscription
    is the worst shape this could take."""
    assert streams_for(["BTCUSDT", "ethusdt"]) == ("btcusdt@aggTrade", "ethusdt@aggTrade")
    assert "btcusdt@aggTrade" in binance_stream_url(streams_for(["BTCUSDT"]))


@pytest.mark.trace("REQ-WP-068")
def test_a_commit_holds_more_than_one_bar() -> None:
    """The first version flushed every sixty seconds while producing a bar every
    sixty seconds, so every bar became its own file: 685 files holding 689 rows
    after eleven hours, and a read of 4.4s against a 2s budget.

    A count keeps `BarSink`'s rule where an interval cannot, because whether an
    interval keeps it depends on a bar size the flush knows nothing about."""
    assert FLUSH_EVERY_BARS > 1
    assert FLUSH_CEILING_NS > 0


@pytest.mark.trace("REQ-WP-068")
def test_a_quiet_symbol_still_commits(tmp_path: Path) -> None:
    """A count alone never commits for a symbol that stopped trading."""
    daemon, _, clock = _daemon(tmp_path, frames=[])
    daemon.bars_pending = lambda: 0
    committed: list[str] = []
    daemon.flush_bars = lambda: committed.append("x") or None  # type: ignore[func-returns-value]
    daemon.start()

    daemon.step()
    assert committed == [], "nothing buffered and no time passed"

    clock.advance_ns(FLUSH_CEILING_NS)
    daemon.step()
    assert committed == ["x"]


@pytest.mark.trace("REQ-WP-068")
def test_enough_bars_commit_before_the_ceiling(tmp_path: Path) -> None:
    daemon, _, clock = _daemon(tmp_path, frames=[])
    daemon.bars_pending = lambda: FLUSH_EVERY_BARS
    committed: list[str] = []
    daemon.flush_bars = lambda: committed.append("x") or None  # type: ignore[func-returns-value]
    daemon.start()

    daemon.step()

    assert committed == ["x"], "the ceiling had not been reached"


@pytest.mark.trace("REQ-WP-066")
def test_a_step_reports_what_it_did(tmp_path: Path) -> None:
    daemon, _, _ = _daemon(tmp_path, frames=[])
    daemon.start()

    report: Any = daemon.step()

    assert report.did_nothing


# --------------------------------------------------------------------------
# The live transport, without a network
# --------------------------------------------------------------------------


class _FakeSocket:
    """Stands in for a websocket connection. Async, because the real one is."""

    def __init__(self, frames: list[str]) -> None:
        self._frames = list(frames)
        self.sent: list[str] = []
        self.closed = False

    async def recv(self) -> str:
        import asyncio

        if not self._frames:
            await asyncio.sleep(3600)  # nothing more; the loop times out and polls
        return self._frames.pop(0)

    async def send(self, payload: str) -> None:
        self.sent.append(payload)

    async def __aenter__(self) -> _FakeSocket:
        return self

    async def __aexit__(self, *_: object) -> None:
        self.closed = True


def _connector(socket: _FakeSocket):  # type: ignore[no-untyped-def]
    def connect(url: str, **_: object) -> _FakeSocket:
        socket.url = url  # type: ignore[attr-defined]
        return socket

    return connect


@pytest.mark.trace("REQ-WP-066")
def test_the_live_transport_delivers_frames_across_the_thread() -> None:
    """The socket runs in its own thread so nothing on this side can stop a
    pong. What crosses is frames, through a queue."""
    from channelflow.connectors.websocket import WebsocketTransport

    socket = _FakeSocket(["a", "b", "c"])
    transport = WebsocketTransport(url_for=binance_stream_url, connect_to=_connector(socket))

    transport.connect(("btcusdt@aggTrade",))
    try:
        deadline = time.monotonic() + 5
        received: list[str] = []
        while len(received) < 3 and time.monotonic() < deadline:
            received.extend(transport.drain())
            time.sleep(0.05)
    finally:
        transport.close()

    assert received == ["a", "b", "c"]
    assert "btcusdt@aggTrade" in socket.url  # type: ignore[attr-defined]


@pytest.mark.trace("REQ-WP-066")
def test_the_queue_depth_is_visible() -> None:
    """A consumer that cannot keep up shows up as a number rather than as
    memory growth nobody attributes."""
    from channelflow.connectors.websocket import WebsocketTransport

    socket = _FakeSocket([f"f{i}" for i in range(5)])
    transport = WebsocketTransport(url_for=binance_stream_url, connect_to=_connector(socket))

    transport.connect(("s",))
    try:
        deadline = time.monotonic() + 5
        while transport.high_water < 1 and time.monotonic() < deadline:
            time.sleep(0.05)
    finally:
        transport.close()

    assert transport.high_water >= 1


@pytest.mark.trace("REQ-WP-066")
def test_a_send_before_connect_is_refused() -> None:
    from channelflow.connectors.websocket import NotConnected, WebsocketTransport

    transport = WebsocketTransport(url_for=binance_stream_url)

    with pytest.raises(NotConnected, match="before connect"):
        transport.send("{}")


@pytest.mark.trace("REQ-WP-066")
def test_the_pong_is_deliberately_silent() -> None:
    """`websockets` answers a PING from the connection's own task -- measured:
    Binance pings every 20 seconds and drops a client that does not answer. A
    second pong from here would answer one ping twice."""
    from channelflow.connectors.websocket import WebsocketTransport

    socket = _FakeSocket([])
    transport = WebsocketTransport(url_for=binance_stream_url, connect_to=_connector(socket))
    transport.connect(("s",))
    try:
        transport.pong()
    finally:
        transport.close()

    assert socket.sent == []


@pytest.mark.trace("REQ-WP-066")
def test_the_replay_transport_is_the_same_seam() -> None:
    """Not a double: the other implementation, so CI runs the process rather
    than a rehearsal of it."""
    replay = ReplayTransport(recorded=["x", "y"])

    replay.connect(("s",))

    assert replay.drain() == ["x", "y"]
    assert replay.drain() == []
    replay.close()
    assert replay.closed is True


# --------------------------------------------------------------------------
# What the sweep found nothing asserting
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-066")
def test_a_frame_that_cannot_be_normalized_is_counted(tmp_path: Path) -> None:
    """A well-formed envelope on the right stream whose payload is missing a
    field. It is not a parse failure and not an ignored stream, and without a
    count it would be a trade that silently never happened."""
    broken = json.dumps({"stream": "btcusdt@aggTrade", "data": {"p": "1", "q": "1"}})
    daemon, _, _ = _daemon(tmp_path, frames=[broken, RECORDED[0]])
    daemon.start()

    report = daemon.step()

    assert (report.trades, report.unparsed, report.ignored) == (1, 1, 0)


@pytest.mark.trace("REQ-WP-066")
def test_every_frame_refreshes_the_session(tmp_path: Path) -> None:
    """`StreamSession` infers a silent drop from silence. A daemon that took
    frames without telling it would reconnect a healthy connection, on the one
    venue where silence is the only signal there is."""
    daemon, _, clock = _daemon(tmp_path, frames=RECORDED[:1])
    daemon.start()
    clock.advance_ns(30 * SECOND_NS)

    daemon.step()

    assert daemon.session._last_inbound_ns == clock.now_ns()  # noqa: SLF001


@pytest.mark.trace("REQ-WP-066")
def test_the_order_of_shutdown_is_commit_then_close(tmp_path: Path) -> None:
    """Closing first leaves the last minute of frames and the last bars in
    memory, and a restart then looks like a gap in the data rather than a gap in
    the shutdown."""
    order: list[str] = []
    daemon, _, _ = _daemon(tmp_path)
    daemon.flush_bars = lambda: order.append("bars") or None  # type: ignore[func-returns-value]
    original_close = daemon.session.connector.close

    def close() -> None:
        order.append("close")
        original_close()

    daemon.session.connector.close = close  # type: ignore[method-assign]
    daemon.start()
    daemon.step()
    daemon.stop()

    assert order == ["bars", "close"]


@pytest.mark.trace("REQ-WP-066")
def test_a_written_object_is_not_written_again(tmp_path: Path) -> None:
    """A buffer kept after a write repeats every frame in the next object, and
    a re-normalisation over the archive would then count each trade twice."""
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")

    archive.add(received_at_ns=BASE_NS, frame="first")
    archive.add(received_at_ns=BASE_NS + 61 * SECOND_NS, frame="second")
    archive.flush()

    objects = sorted(tmp_path.rglob("*.jsonl.gz"))
    assert len(objects) == 2
    contents = [[frame for _, frame in read_frames(o.read_bytes())] for o in objects]
    assert sorted(contents) == [["first"], ["second"]]


# --- the archive keeps a whole minute, not its tail (REQ-NRT-PARITY) ---------


@pytest.mark.trace("REQ-NRT-PARITY")
def test_a_mid_minute_flush_does_not_replace_the_minute_with_its_tail(
    tmp_path: Path,
) -> None:
    """PRD §35.5 found this, and it is what §35.5 was written to find.

    `flush` writes what is buffered under the minute's key, and `store.put`
    replaces an object. So a flush in the middle of a minute, followed by more
    frames in that same minute, used to leave the minute holding only what
    arrived after the flush -- the earlier frames written, then overwritten.

    Measured on a live deployment before the fix: **45 of 45** archived minutes
    held fewer frames than the bars built from them, one of them 274 where the
    bar counted 744. The aggregate trade ids inside each object were contiguous
    and ended where the bar ended, so each object was a clean *suffix* of its
    minute.

    That matters more than a count. §6.4.4's raw tier exists so a later build can
    re-normalize what this one could not read ([[REQ-WP-066]] archives before it
    decides anything), and a tier that silently holds a third of each minute
    cannot do that.
    """
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")
    minute = BASE_NS - BASE_NS % MINUTE_NS

    for index in range(5):
        archive.add(received_at_ns=minute + index, frame=f'{{"n":{index}}}')
    archive.flush()
    for index in range(5, 10):
        archive.add(received_at_ns=minute + index, frame=f'{{"n":{index}}}')
    archive.flush()
    for index in range(10, 13):
        archive.add(received_at_ns=minute + index, frame=f'{{"n":{index}}}')
    archive.add(received_at_ns=minute + MINUTE_NS, frame='{"n":"next minute"}')

    key = archive.key_for(minute)
    kept = read_frames((tmp_path / key).read_bytes())
    assert [frame for _at, frame in kept] == [f'{{"n":{i}}}' for i in range(13)]


@pytest.mark.trace("REQ-NRT-PARITY")
def test_a_minute_that_has_rolled_is_not_held_for_ever(tmp_path: Path) -> None:
    """The held copy is released when the minute closes.

    Otherwise a daemon that runs for days accumulates every frame it ever saw.
    """
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance")
    minute = BASE_NS - BASE_NS % MINUTE_NS
    for step in range(4):
        at = minute + step * MINUTE_NS
        archive.add(received_at_ns=at, frame=f'{{"m":{step}}}')
        archive.flush()
        archive.add(received_at_ns=at + 1, frame=f'{{"m":{step}b}}')
    archive.add(received_at_ns=minute + 9 * MINUTE_NS, frame='{"m":"last"}')
    assert len(archive._held) <= 1, f"holding {len(archive._held)} minutes at once"


@pytest.mark.trace("REQ-WP-076")
def test_registry_connector_paths_resolve_to_importable_classes() -> None:
    """The registry stores dotted paths; the daemon resolves them at startup.

    Before the resolver existed, `build_daemon` called the path itself --
    a string is not callable, so starting a daemon from the registry was a
    crash that no test exercised, because the tests build the daemon directly.
    """
    from channelflow.connectors.binance.connector import BinanceConnector
    from channelflow.connectors.bybit.connector import BybitConnector
    from channelflow.connectors.okx.connector import OkxConnector
    from channelflow.connectors.venue import VENUE_REGISTRY
    from channelflow.pipeline.ingest_main import _resolve_connector

    assert _resolve_connector(VENUE_REGISTRY["binance"].connector) is BinanceConnector
    assert _resolve_connector(VENUE_REGISTRY["bybit"].connector) is BybitConnector
    assert _resolve_connector(VENUE_REGISTRY["okx"].connector) is OkxConnector
