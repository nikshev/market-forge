"""The price bins are collected beside the bars by the ingest daemon (REQ-WP-089)."""

from __future__ import annotations

import queue
import tempfile
from decimal import Decimal

import pytest

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import BINANCE, FakeClock, StreamSession
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline import ingest
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore
from channelflow.pipeline.ingest import IngestDaemon, streams_for
from channelflow.tables import bars as bars_table
from channelflow.tables import volume_bins
from channelflow.volume.bins import PriceBinBuilder

from ..features.conftest import BASE_NS, trade

BLOCK_NS = 300_000_000_000
START = (BASE_NS // BLOCK_NS) * BLOCK_NS
SECOND_NS = 1_000_000_000


class _Connector:
    def __init__(self) -> None:
        self._frames: queue.Queue[str] = queue.Queue()

    def connect(self, streams) -> None:
        pass

    def send(self, payload) -> None:
        pass

    @property
    def alive(self) -> bool:
        return True

    def pong(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def frames(self):
        return self._frames

    def drain_frames(self) -> list[str]:
        return []


def _daemon(tmpdir, *, with_bins: bool):
    catalog = open_catalog(uri="sqlite:///:memory:", warehouse=tmpdir)
    bar_sink = bars_table.BarSink(table=bars_table.table_for(catalog))
    bin_sink = volume_bins.BinSink(table=volume_bins.table_for(catalog))
    connector = _Connector()
    daemon = IngestDaemon(
        session=StreamSession(
            streams=streams_for(["BTCUSDT"]), policy=BINANCE, connector=connector, clock=FakeClock()
        ),
        connector=connector,
        archive=FrameArchive(
            store=LocalObjectStore(root=tmpdir), venue="binance", symbol="BTCUSDT"
        ),
        builder=BarBuilder(timeframe_ns=60_000_000_000, on_final=bar_sink),
        venue="binance",
        flush_bars=bar_sink.flush,
        bars_pending=lambda: bar_sink.pending,
        bins=PriceBinBuilder(
            block_ns=BLOCK_NS, bin_width=Decimal("10"), sequential_ids=True, on_final=bin_sink
        )
        if with_bins
        else None,
        flush_bins=bin_sink.flush,
        bins_pending=lambda: bin_sink.pending,
    )
    return daemon, catalog, bar_sink, bin_sink


def _feed(monkeypatch, daemon, trades) -> None:
    monkeypatch.setattr(ingest, "normalize_frames", lambda **_: (list(trades), 0, 0, 0))
    daemon._consume("frame", START)


@pytest.mark.trace("REQ-WP-089")
def test_a_trade_reaches_the_bin_builder_beside_the_bar_builder(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        daemon, _, bar_sink, bin_sink = _daemon(tmpdir, with_bins=True)
        trades = [
            trade("1", "100", "2", "buy", at_ns=START + SECOND_NS),
            trade("2", "105", "3", "sell", at_ns=START + 2 * SECOND_NS),
            trade("3", "100", "1", "buy", at_ns=START + BLOCK_NS + 6 * SECOND_NS),
        ]

        _feed(monkeypatch, daemon, trades)

        assert bin_sink.pending == 1  # one bin (100-110) of the block that closed
        assert daemon.builder.late_trade_count == 0


@pytest.mark.trace("REQ-WP-089")
def test_the_bars_are_unchanged_by_collecting_bins(monkeypatch) -> None:
    results = {}
    for with_bins in (False, True):
        with tempfile.TemporaryDirectory() as tmpdir:
            daemon, catalog, bar_sink, _ = _daemon(tmpdir, with_bins=with_bins)
            _feed(
                monkeypatch,
                daemon,
                [
                    trade("1", "100", "2", "buy", at_ns=START + SECOND_NS),
                    trade("2", "105", "3", "sell", at_ns=START + 70 * SECOND_NS),
                    trade("3", "100", "1", "buy", at_ns=START + 140 * SECOND_NS),
                ],
            )
            results[with_bins] = list(bar_sink._buffer)

    assert results[False] == results[True]


@pytest.mark.trace("REQ-WP-089")
def test_a_daemon_without_a_bin_builder_collects_nothing_and_does_not_fail(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        daemon, _, _, bin_sink = _daemon(tmpdir, with_bins=False)

        _feed(monkeypatch, daemon, [trade("1", "100", "2", "buy", at_ns=START + SECOND_NS)])

        assert bin_sink.pending == 0


@pytest.mark.trace("REQ-WP-089")
def test_the_flush_commits_the_bins_with_the_bars(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        daemon, catalog, _, bin_sink = _daemon(tmpdir, with_bins=True)
        _feed(
            monkeypatch,
            daemon,
            [
                trade("1", "100", "2", "buy", at_ns=START + SECOND_NS),
                trade("2", "100", "1", "buy", at_ns=START + BLOCK_NS + 6 * SECOND_NS),
            ],
        )
        assert bin_sink.pending == 1

        daemon.flush_bars()
        daemon.flush_bins()

        read = volume_bins.read_bins(
            volume_bins.table_for(catalog), venue="binance", symbol="BTCUSDT"
        )
        assert len(read.rows) == 1
        assert read.rows[0].buy == Decimal("2")
