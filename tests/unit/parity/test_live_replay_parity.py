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
from channelflow.connectors.session import BINANCE, StreamSession
from channelflow.connectors.websocket import ReplayTransport
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore, read_frames
from channelflow.pipeline.ingest import IngestDaemon, streams_for

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
    daemon = IngestDaemon(
        session=StreamSession(
            streams=streams_for(["BTCUSDT"]), policy=BINANCE, transport=transport, clock=clock
        ),
        transport=transport,
        archive=FrameArchive(store=LocalObjectStore(root=tmp_path), venue="binance"),
        builder=builder,
        venue="binance",
        now_ns=clock,
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
    assert len(list((FIXTURES / "frames").glob("*.jsonl.gz"))) == manifest["minutes"]


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
def test_the_captured_segment_is_short_because_the_archive_was_losing_frames() -> None:
    """The fixture is evidence, and this names what of.

    §35.5's parity assertion cannot run on it. The segment was captured from a
    deployment whose `FrameArchive.flush` replaced a minute with its own tail --
    a mid-minute flush wrote what it had, `store.put` replaced the object, and
    the frames that arrived afterwards were written alone when the minute
    closed. `test_a_mid_minute_flush_does_not_replace_the_minute_with_its_tail`
    proves the mechanism and guards the fix.

    So every one of these forty-five minutes holds a clean *suffix*: the
    aggregate trade ids inside each object are contiguous and end where the live
    bar ends, and begin later than it begins. This test pins that shape, because
    it is the only thing this fixture can honestly demonstrate -- and because a
    later capture that still looks like this would mean the fix did not take.
    """
    live = {int(row["open_time_ns"]) // MINUTE_NS: row for row in _live_bars()}
    short = 0
    for path in sorted((FIXTURES / "frames").glob("*.jsonl.gz")):
        frames = read_frames(path.read_bytes())
        ids = [json.loads(frame)["data"]["a"] for _at, frame in frames]
        assert ids == list(range(ids[0], ids[0] + len(ids))), (
            f"{path.name} has gaps inside it; this fixture's loss is a lost prefix, "
            "not scattered frames"
        )
        minute = frames[0][0] // MINUTE_NS
        row = live.get(minute)
        if row is None:
            continue
        # Measured across all forty-five: 19 to 465 frames missing at the start,
        # and nought or one at the end. The end is the ordinary skew between
        # receipt and event time at a minute boundary -- a trade at :59.99 can
        # be received at :00.01 and archived under the next minute. The start is
        # the overwrite.
        assert int(row["last_trade_id"]) - ids[-1] <= 1, (
            f"{path.name} is short at its END by "
            f"{int(row['last_trade_id']) - ids[-1]}; the loss here was a prefix"
        )
        assert ids[0] > int(row["first_trade_id"]), f"{path.name} is not short at its start"
        short += 1
    assert short == 45, f"{short} of 45 minutes are short; the fixture is pre-fix evidence"
