"""One object per venue, symbol and minute (REQ-WP-078).

# @trace: REQ-WP-078

Three Binance processes -- BTCUSDT, ETHUSDT, SOLUSDT -- wrote one key between them
because it named the venue and the minute and nothing else. `store.put` replaces an
object, so the last process to flush a minute won and the other two symbols' frames
for it were gone. Sampled minutes each held exactly one symbol.

The assertions here read frames back. The earlier mistake was a key that looked
right as a string, so comparing keys would be the test that cannot see it.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from channelflow.pipeline.archive import (
    FrameArchive,
    LocalObjectStore,
    S3ObjectStore,
    read_frames,
)

from .fake_s3 import FakeS3

MINUTE_NS = 60_000_000_000
NOW = 1_790_000_000_000_000_000

#: The logger these tests are about. `caplog` collects from **every** logger while a
#: test runs, and other tests in the suite leave reader threads that log on their own
#: schedule; counting all records made this fail in the full suite and pass alone.
ARCHIVE_LOG = "channelflow.pipeline.archive"


def _archive_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == ARCHIVE_LOG and r.levelno >= logging.INFO]


def _frame(symbol: str, n: int) -> str:
    return json.dumps({"stream": f"{symbol.lower()}@aggTrade", "data": {"s": symbol, "n": n}})


@pytest.mark.trace("REQ-WP-078")
def test_two_symbols_of_one_venue_in_one_minute_leave_two_objects(tmp_path: Path) -> None:
    store = LocalObjectStore(root=tmp_path)
    btc = FrameArchive(store=store, venue="binance", symbol="BTCUSDT")
    eth = FrameArchive(store=store, venue="binance", symbol="ETHUSDT")

    for n in range(3):
        btc.add(received_at_ns=NOW + n, frame=_frame("BTCUSDT", n))
        eth.add(received_at_ns=NOW + n, frame=_frame("ETHUSDT", n))
    btc.flush()
    eth.flush()

    objects = sorted(tmp_path.rglob("*.jsonl.gz"))
    assert len(objects) == 2, [p.relative_to(tmp_path).as_posix() for p in objects]
    held = {}
    for path in objects:
        streams = {json.loads(frame)["stream"] for _, frame in read_frames(path.read_bytes())}
        held[path.parent.parent.parent.parent.name] = streams
    # Read from the frames, not the keys: each object holds only its own symbol.
    assert held == {"BTCUSDT": {"btcusdt@aggTrade"}, "ETHUSDT": {"ethusdt@aggTrade"}}


@pytest.mark.trace("REQ-WP-078")
def test_the_key_names_venue_symbol_and_receipt_minute(tmp_path: Path) -> None:
    archive = FrameArchive(
        store=LocalObjectStore(root=tmp_path), venue="okx", symbol="BTC-USDT-SWAP"
    )

    key = archive.key_for(NOW - NOW % MINUTE_NS)

    parts = key.split("/")
    assert parts[:4] == ["raw", "cex", "okx", "BTC-USDT-SWAP"]
    assert len(parts) == 8 and parts[-1].endswith(".jsonl.gz")


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("venue", "symbol"),
    [("binance", ""), ("binance", "BTC/USDT"), ("", "BTCUSDT"), ("bin/ance", "BTCUSDT")],
)
def test_an_empty_name_or_one_containing_a_slash_is_refused(
    tmp_path: Path, venue: str, symbol: str
) -> None:
    """A slash would nest, and the key would stop meaning what its parts say."""
    with pytest.raises(ValueError, match="venue|symbol"):
        FrameArchive(store=LocalObjectStore(root=tmp_path), venue=venue, symbol=symbol)


@pytest.mark.trace("REQ-WP-078")
def test_a_flush_with_nothing_to_write_says_nothing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Bybit's log carried this line five times a second, for an empty buffer."""
    archive = FrameArchive(store=LocalObjectStore(root=tmp_path), venue="bybit", symbol="BTCUSDT")
    caplog.set_level(logging.INFO)

    for _ in range(50):
        assert archive.flush() is None

    assert _archive_records(caplog) == []


@pytest.mark.trace("REQ-WP-078")
def test_a_flush_that_writes_logs_once_even_through_s3(caplog: pytest.LogCaptureFixture) -> None:
    """The S3 store used to add its own line per put on top of the archive's."""
    client = FakeS3()
    archive = FrameArchive(
        store=S3ObjectStore(bucket="b", client=client), venue="binance", symbol="BTCUSDT"
    )
    archive.add(received_at_ns=NOW, frame=_frame("BTCUSDT", 1))
    caplog.set_level(logging.INFO)

    assert archive.flush() is not None

    assert len(_archive_records(caplog)) == 1
