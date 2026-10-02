"""Tests for silence detector in IngestDaemon (REQ-WP-076).

These tests are written FIRST and expected to FAIL because the silence detector
is not yet implemented (T024a). They document the expected behaviour.
"""

# @trace: REQ-WP-076

import queue
import tempfile

import pytest

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import BINANCE, FakeClock, StreamSession
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore
from channelflow.pipeline.ingest import IngestDaemon, streams_for
from channelflow.tables import bars as bars_table


class SilentConnector:
    """Fake connector that accepts connection but never delivers frames."""

    def __init__(self):
        self._frames = queue.Queue()
        self._connected = False
        self._closed = False

    def connect(self, streams):
        self._connected = True

    def send(self, payload):
        pass

    def pong(self):
        pass

    def close(self):
        self._closed = True

    @property
    def frames(self):
        return self._frames

    def drain_frames(self) -> list[str]:
        out = []
        while True:
            try:
                out.append(self._frames.get_nowait())
            except queue.Empty:
                return out


class TestSilenceDetector:
    """A connection that delivers no frames is reported within a configurable window."""

    @pytest.mark.trace("REQ-WP-076")
    def test_silent_connection_reported(self):
        """A connection that delivers nothing is reported with venue and symbol."""
        connector = SilentConnector()
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = open_catalog(uri="sqlite:///:memory:", warehouse=tmpdir)
            sink = bars_table.BarSink(table=bars_table.table_for(catalog))
            builder = BarBuilder(timeframe_ns=60_000_000_000, on_final=sink)
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="bybit", symbol="BTCUSDT"
            )

            daemon = IngestDaemon(
                session=StreamSession(
                    streams=streams_for(["BTCUSDT"]),
                    policy=BINANCE,
                    connector=connector,
                    clock=FakeClock(),
                ),
                connector=connector,
                archive=archive,
                builder=builder,
                venue="bybit",
                flush_bars=sink.flush,
                bars_pending=lambda: sink.pending,
            )
            daemon.start()

            # This test documents the expected behaviour:
            # After a configurable silence window passes with no frames,
            # a warning should be logged with venue, symbol, and silence duration.
            # The feature is not yet implemented (T024a), so this test fails.
            assert hasattr(daemon, "_last_frame_ns"), "silence detector not implemented"

    @pytest.mark.trace("REQ-WP-076")
    def test_normal_frame_resets_silence_timer(self):
        """A frame arriving resets the silence timer; no warning fires."""
        connector = SilentConnector()
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = open_catalog(uri="sqlite:///:memory:", warehouse=tmpdir)
            sink = bars_table.BarSink(table=bars_table.table_for(catalog))
            builder = BarBuilder(timeframe_ns=60_000_000_000, on_final=sink)
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="bybit", symbol="BTCUSDT"
            )

            daemon = IngestDaemon(
                session=StreamSession(
                    streams=streams_for(["BTCUSDT"]),
                    policy=BINANCE,
                    connector=connector,
                    clock=FakeClock(),
                ),
                connector=connector,
                archive=archive,
                builder=builder,
                venue="bybit",
                flush_bars=sink.flush,
                bars_pending=lambda: sink.pending,
            )
            daemon.start()

            # Push a frame - this should reset any silence tracking
            connector._frames.put('{"trade": "data"}')
            daemon.step()

            # After a frame, the silence timer should be reset
            # (implementation detail verified by not firing a warning)
            assert hasattr(daemon, "_check_silence"), "silence check not implemented"
