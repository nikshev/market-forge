"""Silence, judged through the daemon that carries it (REQ-WP-076, REQ-WP-078).

# @trace: REQ-WP-076
# @trace: REQ-WP-078

The first version of this file asserted `hasattr(daemon, "_last_frame_ns")`: that an
attribute existed, not that anything happened. It passed beside a Binance feed that sat
silent for four days. These tests drive an `IngestDaemon` and read what the connector was
asked to do and what the log said.
"""

from __future__ import annotations

import logging

import pytest

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import OKX, SECOND_NS, FakeClock, StreamSession
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore
from channelflow.pipeline.ingest import IngestDaemon

from .fakes import ControllableConnector


def _daemon(tmp_path):  # type: ignore[no-untyped-def]
    clock = FakeClock(1_790_000_000 * SECOND_NS)
    connector = ControllableConnector()
    connector.now_ns = clock.now_ns
    daemon = IngestDaemon(
        session=StreamSession(
            ("trades.BTC-USDT-SWAP",), policy=OKX, connector=connector, clock=clock
        ),
        connector=connector,
        archive=FrameArchive(
            store=LocalObjectStore(root=tmp_path), venue="okx", symbol="BTC-USDT-SWAP"
        ),
        builder=BarBuilder(timeframe_ns=60 * SECOND_NS, on_final=lambda bar: None),
        venue="okx",
        now_ns=clock.now_ns,
    )
    daemon.start()
    return daemon, connector, clock


@pytest.mark.trace("REQ-WP-076")
@pytest.mark.trace("REQ-WP-078")
def test_a_silent_connection_is_reported_with_the_venue_and_reconnected(
    tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    daemon, connector, clock = _daemon(tmp_path)
    caplog.set_level(logging.INFO)

    clock.advance_ns(OKX.max_silence_ns + SECOND_NS)
    daemon.step()

    assert connector.closed == 1 and len(connector.connects) == 2
    said = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("okx" in m and "silent" in m for m in said), said


@pytest.mark.trace("REQ-WP-076")
@pytest.mark.trace("REQ-WP-078")
def test_a_frame_arriving_resets_the_silence_timer(tmp_path) -> None:  # type: ignore[no-untyped-def]
    daemon, connector, clock = _daemon(tmp_path)
    limit = OKX.max_silence_ns
    assert limit is not None

    clock.advance_ns(limit - 20 * SECOND_NS)
    connector.push("a frame")
    daemon.step()
    clock.advance_ns(limit - 20 * SECOND_NS)  # the same again: past the limit from the start
    daemon.step()
    assert connector.closed == 0, "a frame must restart the silence timer"

    clock.advance_ns(21 * SECOND_NS)  # now past the limit since that frame
    daemon.step()
    assert connector.closed == 1
