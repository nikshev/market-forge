"""Tests for FrameArchive venue prefix (REQ-WP-076)."""

# @trace: REQ-WP-076

import tempfile

import pytest

from channelflow.pipeline.archive import FrameArchive, LocalObjectStore


class TestFrameArchivePrefix:
    """FrameArchive prefixes objects with the venue name."""

    @pytest.mark.trace("REQ-WP-076")
    def test_bybit_venue_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FrameArchive(store=LocalObjectStore(root=tmpdir), venue="bybit")
            key = archive.key_for(0)
            assert key.startswith("raw/cex/bybit/")

    @pytest.mark.trace("REQ-WP-076")
    def test_okx_venue_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FrameArchive(store=LocalObjectStore(root=tmpdir), venue="okx")
            key = archive.key_for(0)
            assert key.startswith("raw/cex/okx/")

    @pytest.mark.trace("REQ-WP-076")
    def test_binance_venue_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = FrameArchive(store=LocalObjectStore(root=tmpdir), venue="binance")
            key = archive.key_for(0)
            assert key.startswith("raw/cex/binance/")
