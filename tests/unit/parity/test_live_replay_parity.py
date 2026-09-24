"""PRD §35.5: a captured live segment replays to the same outputs.

    Capture a 30-60 minute live event segment.
    Replay it offline.
    Assert feature/channel/signal parity.

The fixture is both halves of that comparison, taken from a running deployment
by `tools.record.parity_capture`: forty-five minutes of frames **exactly as the
archive wrote them**, and the forty-five bars the live run produced from them.

**Why this is not [[REQ-NRT-E]] again.** That test runs `detector().run(history)`
twice in one process and compares. It proves determinism, which is worth
proving. This drives the frames through the archive's own reader, the same
`ReplayTransport` a backfill uses, and the same `IngestDaemon` the deployment
runs — so a timestamp narrowed on the way to disk, a frame ordered differently,
or a field the archive drops would show here and cannot show there.

**Boundary minutes are excluded by construction.** The capture takes one minute
of margin at each end, because a bar spanning the segment's edge saw trades the
segment does not hold. A tolerance wide enough to accept such a bar would be
wide enough to hide a real difference.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from channelflow.bars import BarBuilder
from channelflow.channels import RollingOLSChannel
from channelflow.connectors.session import BINANCE, StreamSession
from channelflow.connectors.websocket import ReplayTransport
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore, read_frames
from channelflow.pipeline.ingest import IngestDaemon, streams_for
from channelflow.signals import SignalMachine
from channelflow.connectors.venue import VENUE_REGISTRY, VenueConnector

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "parity"
MINUTE_NS = 60_000_000_000

#: Compared field by field. `vwap` is a ratio the builder carries at full
#: precision, and it is included: a replay that got the volumes right and the
#: ratio wrong would be a replay with a bug.
COMPARED = (
    "open_time_ns",
    "close_time_ns",
    "open",
    "high",
    "low",
    "close",
    "volume_base",
    "volume_quote",
    "trade_count",
    "vwap",
    "delta_base",
    "aggressive_buy_base",
    "aggressive_sell_base",
    "first_trade_id",
    "last_trade_id",
    "high_time_ns",
    "low_time_ns",
)


def _manifest() -> dict:
    return json.loads((FIXTURES / "manifest.json").read_text())


def _live_bars() -> list[dict]:
    rows = [json.loads(line) for line in (FIXTURES / "bars.jsonl").read_text().splitlines()]
    return sorted(rows, key=lambda row: int(row["open_time_ns"]))


def _archived_frames() -> list[tuple[int, str]]:
    """Every frame the segment holds, in the order the socket delivered them."""
    frames: list[tuple[int, str]] = []
    for path in sorted((FIXTURES / "frames").glob("*.jsonl.gz")):
        frames.extend(read_frames(path.read_bytes()))
    return frames


class _Clock:
    """Event time from the frames, so the replay is not driven by a wall clock."""

    def __init__(self, first_ns: int) -> None:
        self.now = first_ns

    def __call__(self) -> int:
        return self.now

    def now_ns(self) -> int:
        """`StreamSession` asks for a clock object; `IngestDaemon` for a callable."""
        return self.now


def _replayed_bars(tmp_path: Path) -> list:
    """The same daemon, the same transport, fed what the archive kept."""
    frames = _archived_frames()
    assert frames, "the fixture holds no frames"
    clock = _Clock(frames[0][0])
    produced: list = []
    transport = ReplayTransport(recorded=[frame for _at, frame in frames])
    builder = BarBuilder(timeframe_ns=MINUTE_NS, grace_ns=5_000_000_000, on_final=produced.append)
    
    # Wrap ReplayTransport in a VenueConnector for the new interface
    class ReplayConnector:
        def __init__(self, transport):
            self._transport = transport
            
        def connect(self, streams: tuple[str, ...]) -> None:
            self._transport.connect(streams)
            
        def send(self, payload: str) -> None:
            self._transport.send(payload)
            
        def pong(self) -> None:
            self._transport.pong()
            
        def close(self) -> None:
            self._transport.close()
            
        @property
        def frames(self):
            return self._transport
    
    config = VENUE_REGISTRY["binance"]
    connector = ReplayConnector(transport)
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
    # Received-at drives the archive, so it advances with the frames rather than
    # sitting still: a clock that never moved would write one object and mask
    # any ordering fault in the reader.
    for received_at, _frame in frames:
        clock.now = received_at
        daemon.step()
    clock.now = frames[-1][0] + 10 * MINUTE_NS
    daemon.step()
    return sorted(produced, key=lambda bar: bar.open_time_ns)


@pytest.fixture(scope="module")
def replayed(tmp_path_factory: pytest.TempPathFactory) -> list:
    return _replayed_bars(tmp_path_factory.mktemp("parity"))


# --- the fixture is what it claims -------------------------------------------


@pytest.mark.trace("REQ-NRT-PARITY")
def test_the_segment_is_the_length_the_section_asks_for() -> None:
    """§35.5 says 30-60 minutes. A shorter one is not the segment it asks for."""
    manifest = _manifest()
    assert 30 <= manifest["minutes"] <= 60
    span = manifest["window_end_ns"] - manifest["window_start_ns"]
    assert span == manifest["minutes"] * MINUTE_NS
    # One object more than compared minutes: the trailing one closes the last
    # bar, because the builder finalizes a minute when a trade arrives after it.
    assert len(list((FIXTURES / "frames").glob("*.jsonl.gz"))) == manifest["objects"]
    assert manifest["objects"] == manifest["minutes"] + 1


@pytest.mark.trace("REQ-NRT-PARITY")
def test_the_frames_are_what_the_archive_wrote() -> None:
    """Read through the archive's own reader, not a re-serialisation."""
    frames = _archived_frames()
    assert len(frames) > 1_000, f"only {len(frames)} frames in 45 minutes"
    assert frames == sorted(frames, key=lambda row: row[0]), "frames are out of order"
    first = json.loads(frames[0][1])
    assert first["data"]["e"] == "aggTrade"
    assert first["data"]["s"] == "BTCUSDT"


@pytest.mark.trace("REQ-NRT-PARITY")
def test_every_archived_object_is_still_gzip() -> None:
    """Copied byte for byte. A fixture that had been decoded proves less."""
    for path in sorted((FIXTURES / "frames").glob("*.jsonl.gz")):
        assert gzip.decompress(path.read_bytes()), f"{path.name} is empty"


# --- what the captured segment proves about the archive ----------------------


@pytest.mark.trace("REQ-NRT-PARITY")
def test_every_archived_minute_is_whole() -> None:
    """The archive keeps all of a minute, and this is how we know.

    Before [[REQ-NRT-PARITY]], `FrameArchive.flush` replaced a minute with its
    own tail: a mid-minute flush wrote what it had, `store.put` replaced the
    object, and the frames arriving afterwards were written alone when the
    minute closed. Measured then, on a segment captured from the deployment:
    **45 of 45** minutes short, between 19 and 465 frames missing from the start
    of each, the worst holding 274 of 744.

    This segment was captured after the fix, from the same deployment. Every
    minute now begins where its bar begins.

    The end is allowed to be one short. That is the ordinary skew between
    receipt and event time at a boundary -- a trade at `:59.99` can be received
    at `:00.01` and archived under the next minute -- and it is a measured
    distribution rather than a chosen tolerance.
    """
    live = {int(row["open_time_ns"]) // MINUTE_NS: row for row in _live_bars()}
    checked = 0
    for path in sorted((FIXTURES / "frames").glob("*.jsonl.gz")):
        frames = read_frames(path.read_bytes())
        ids = [json.loads(frame)["data"]["a"] for _at, frame in frames]
        assert ids == list(range(ids[0], ids[0] + len(ids))), f"{path.name} has gaps inside it"
        row = live.get(frames[0][0] // MINUTE_NS)
        if row is None:
            continue
        # Measured across all thirty minutes of this segment: the start offset
        # is -1 or 0 and the end offset 0 or 1. At most one trade either side,
        # in either direction, which is the receipt/event skew at a boundary and
        # not a loss. Before the fix the start offset ran from 19 to 465, always
        # positive -- the archive beginning late is the whole signature.
        start_offset = ids[0] - int(row["first_trade_id"])
        end_offset = int(row["last_trade_id"]) - ids[-1]
        assert -1 <= start_offset <= 1, (
            f"{path.name} starts {start_offset} trades from its bar; the archive is "
            "losing the beginning of the minute again"
        )
        assert -1 <= end_offset <= 1, f"{path.name} ends {end_offset} trades from its bar"
        checked += 1
    assert checked == _manifest()["minutes"], f"only {checked} minutes were checked"


# --- §35.5's own assertion: feature, channel and signal parity ---------------
#
# These run against the whole chain: frames -> bars -> channels -> signals. They
# cannot pass on a fixture captured from the broken archive, which is why
# REQ-NRT-PARITY waits for a segment taken after the fix.

LOOKBACK = 20


def _live_as_bars() -> list:
    """The live rows rebuilt as `Bar`s, so both sides feed the same code.

    Every field the plane stores comes straight from the row. `is_final` is the
    one it does not: the canonical plane holds finalized bars only, so a stored
    bar is final by definition and reconstructing it as anything else would be
    inventing a state the row never had.
    """
    from channelflow.bars import Bar

    return [Bar(is_final=True, **row) for row in _live_bars()]


def _inside(bars: list) -> list:
    manifest = _manifest()
    return sorted(
        (
            bar
            for bar in bars
            if manifest["window_start_ns"] <= bar.open_time_ns
            and bar.close_time_ns <= manifest["window_end_ns"]
        ),
        key=lambda bar: bar.open_time_ns,
    )


def _channels(bars: list) -> list:
    """One snapshot per moment the model can answer about."""
    return [
        RollingOLSChannel(lookback=LOOKBACK).fit(
            bars[: index + 1], as_of_ns=bars[index].close_time_ns
        )
        for index in range(LOOKBACK - 1, len(bars))
    ]


def _signals(bars: list, snapshots: list) -> list:
    machine = SignalMachine()
    seen = []
    for bar, snapshot in zip(bars[LOOKBACK - 1 :], snapshots, strict=True):
        candidate = machine.on_bar(bar, snapshot)
        if candidate is not None:
            seen.append((bar.close_time_ns, candidate.state, candidate.side))
    return seen


@pytest.mark.trace("REQ-NRT-PARITY")
def test_the_replayed_bars_are_the_live_bars(replayed: list) -> None:
    """§35.5 step three, on the bars themselves."""
    live = _live_as_bars()
    mine = _inside(replayed)
    assert len(live) == len(mine) > 0, f"live {len(live)}, replay {len(mine)}"
    differences = []
    for theirs, ours in zip(live, mine, strict=True):
        for field in ("open_time_ns", "open", "high", "low", "close", "volume_base", "trade_count"):
            if getattr(theirs, field) != getattr(ours, field):
                differences.append(
                    f"minute {theirs.open_time_ns}, {field}: "
                    f"live {getattr(theirs, field)!r}, replay {getattr(ours, field)!r}"
                )
    assert differences == [], "\n".join(differences[:8])


@pytest.mark.trace("REQ-NRT-PARITY")
def test_the_channels_fitted_over_each_are_identical(replayed: list) -> None:
    live = _channels(_live_as_bars())
    mine = _channels(_inside(replayed))
    assert len(live) == len(mine) > 0
    for theirs, ours in zip(live, mine, strict=True):
        assert theirs == ours, f"at {theirs.as_of_ns}: live {theirs}, replay {ours}"


@pytest.mark.trace("REQ-NRT-PARITY")
def test_the_signals_are_the_same_in_the_same_order(replayed: list) -> None:
    """Fewer fails, and so does more."""
    live_bars, mine_bars = _live_as_bars(), _inside(replayed)
    live = _signals(live_bars, _channels(live_bars))
    mine = _signals(mine_bars, _channels(mine_bars))
    assert live == mine, f"live {live}\nreplay {mine}"
