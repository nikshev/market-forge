"""Tests for IngestDaemon with VenueConnector (REQ-WP-076)."""

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


class FakeVenueConnector:
    """Fake VenueConnector for testing IngestDaemon."""

    def __init__(self):
        self._frames = queue.Queue()
        self._connected = False
        self._closed = False
        self.connected_streams = None
        self.sent_payloads = []

    def connect(self, streams):
        self._connected = True
        self.connected_streams = streams

    def send(self, payload):
        self.sent_payloads.append(payload)

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


class TestIngestDaemonWithVenue:
    """IngestDaemon built from config writes bars with venue and archives under venue prefix."""

    @pytest.mark.trace("REQ-WP-076")
    def test_daemon_connect_called_with_correct_streams(self):
        connector = FakeVenueConnector()
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

            assert connector.connected_streams == streams_for(["BTCUSDT"])

    @pytest.mark.trace("REQ-WP-076")
    def test_daemon_venue_attribute(self):
        connector = FakeVenueConnector()
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

            assert daemon.venue == "bybit"

    @pytest.mark.trace("REQ-WP-076")
    def test_archive_prefix_contains_venue(self):
        connector = FakeVenueConnector()
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = open_catalog(uri="sqlite:///:memory:", warehouse=tmpdir)
            sink = bars_table.BarSink(table=bars_table.table_for(catalog))
            builder = BarBuilder(timeframe_ns=60_000_000_000, on_final=sink)
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="okx", symbol="BTC-USDT-SWAP"
            )

            _ = IngestDaemon(
                session=StreamSession(
                    streams=streams_for(["BTC-USDT-SWAP"]),
                    policy=BINANCE,
                    connector=connector,
                    clock=FakeClock(),
                ),
                connector=connector,
                archive=archive,
                builder=builder,
                venue="okx",
                flush_bars=sink.flush,
                bars_pending=lambda: sink.pending,
            )

            # The archive prefix should contain the venue (format: raw/cex/venue/...)
            key = archive.key_for(0)
            assert "okx" in key
            assert key.startswith("raw/cex/okx/BTC-USDT-SWAP/")
