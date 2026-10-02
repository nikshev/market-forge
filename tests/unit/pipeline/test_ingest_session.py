"""Tests for StreamSession with VenueConnector (REQ-WP-076)."""

# @trace: REQ-WP-076

import queue

import pytest

from channelflow.connectors.session import BINANCE, FakeClock
from channelflow.pipeline.ingest import StreamSession, streams_for


class FakeVenueConnector:
    """Fake VenueConnector for testing StreamSession."""

    def __init__(self):
        self._frames = queue.Queue()
        self._connected = False
        self._closed = False
        self.connected_streams = None
        self.sent_payloads = []
        self.pong_called = False

    def connect(self, streams):
        self._connected = True
        self.connected_streams = streams

    def send(self, payload):
        self.sent_payloads.append(payload)

    @property
    def alive(self) -> bool:
        """A fake whose reader never ends. `kill()` lives in `pipeline/fakes.py`."""
        return True

    def pong(self):
        self.pong_called = True

    def close(self):
        self._closed = True

    @property
    def frames(self):
        return self._frames

    def drain_frames(self) -> list[str]:
        """Drain all available frames from the queue."""
        out = []
        while True:
            try:
                out.append(self._frames.get_nowait())
            except queue.Empty:
                return out


class TestStreamSessionWithVenueConnector:
    """StreamSession accepts a VenueConnector and delegates to it."""

    @pytest.mark.trace("REQ-WP-076")
    def test_session_accepts_fake_connector(self):
        connector = FakeVenueConnector()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=BINANCE,
            connector=connector,
            clock=FakeClock(),
        )
        assert session.connector is connector

    @pytest.mark.trace("REQ-WP-076")
    def test_session_calls_connect_on_start(self):
        connector = FakeVenueConnector()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=BINANCE,
            connector=connector,
            clock=FakeClock(),
        )
        # StreamSession.start() should call connector.connect(streams)
        session.start()
        assert connector._connected
        assert connector.connected_streams == streams_for(["BTCUSDT"])

    @pytest.mark.trace("REQ-WP-076")
    def test_session_reads_frames_from_connector(self):
        connector = FakeVenueConnector()
        session = StreamSession(
            streams=streams_for(["BTCUSDT"]),
            policy=BINANCE,
            connector=connector,
            clock=FakeClock(),
        )
        session.start()
        # Push a frame through the connector
        connector._frames.put('{"trade": "data"}')
        frames = connector.drain_frames()
        assert len(frames) == 1
        assert frames[0] == '{"trade": "data"}'

    @pytest.mark.trace("REQ-WP-076")
    def test_session_close_delegates_to_connector(self):
        import tempfile

        from channelflow.bars.builder import BarBuilder
        from channelflow.lakehouse import catalog as open_catalog
        from channelflow.pipeline.archive import LocalObjectStore
        from channelflow.pipeline.ingest import FrameArchive, IngestDaemon
        from channelflow.tables import bars as bars_table

        connector = FakeVenueConnector()
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = open_catalog(uri="sqlite:///:memory:", warehouse=tmpdir)
            sink = bars_table.BarSink(table=bars_table.table_for(catalog))
            builder = BarBuilder(timeframe_ns=60_000_000_000, on_final=sink)
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="binance", symbol="BTCUSDT"
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
                venue="binance",
                flush_bars=sink.flush,
                bars_pending=lambda: sink.pending,
            )
            daemon.stop()
            assert connector._closed
