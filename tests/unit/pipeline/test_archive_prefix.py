"""Tests for FrameArchive key layout (REQ-WP-076, REQ-WP-078).

These test the **class**. What `build_daemon` hands the class is tested in
`test_build_daemon_seams.py`, which is where the earlier mistake was: this file built
`FrameArchive` with its default prefix and so passed against a wiring that never used it.
"""

# @trace: REQ-WP-076
# @trace: REQ-WP-078

import tempfile

import pytest

from channelflow.pipeline.archive import FrameArchive, LocalObjectStore


class TestFrameArchivePrefix:
    """FrameArchive prefixes objects with the venue name."""

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_venue_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="bybit", symbol="BTCUSDT"
            )
            key = archive.key_for(0)
            assert key.startswith("raw/cex/bybit/BTCUSDT/")

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_venue_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="okx", symbol="BTC-USDT-SWAP"
            )
            key = archive.key_for(0)
            assert key.startswith("raw/cex/okx/BTC-USDT-SWAP/")

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_venue_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FrameArchive(
                store=LocalObjectStore(root=tmpdir), venue="binance", symbol="BTCUSDT"
            )
            key = archive.key_for(0)
            assert key.startswith("raw/cex/binance/BTCUSDT/")
