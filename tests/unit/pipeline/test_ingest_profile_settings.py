"""The price bin settings of the ingest daemon (REQ-WP-089, Principle X)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.pipeline.ingest_main import (
    PROFILE_BIN_WIDTHS,
    PROFILE_BLOCK_SECONDS,
    ingest_settings_from_env,
)
from channelflow.settings import MissingConfiguration

BASE = {
    "CHANNELFLOW_INGEST_SYMBOLS": "BTCUSDT",
    "CHANNELFLOW_ARCHIVE_URI": "s3://bucket/raw/cex",
}


@pytest.mark.trace("REQ-WP-089")
def test_unset_means_each_symbol_derives_its_own_width_and_the_block_is_five_minutes() -> None:
    settings = ingest_settings_from_env(BASE)

    assert settings.profile_bin_widths == {}
    assert settings.profile_block_ns == 300_000_000_000


@pytest.mark.trace("REQ-WP-089")
def test_the_widths_and_the_block_length_are_read_from_the_environment() -> None:
    settings = ingest_settings_from_env(
        {
            **BASE,
            PROFILE_BIN_WIDTHS: "binance:BTCUSDT=20,okx:BTC-USDT-SWAP=0.5",
            PROFILE_BLOCK_SECONDS: "600",
        }
    )

    assert settings.profile_bin_widths == {
        ("binance", "BTCUSDT"): Decimal("20"),
        ("okx", "BTC-USDT-SWAP"): Decimal("0.5"),
    }
    assert settings.profile_block_ns == 600_000_000_000


@pytest.mark.trace("REQ-WP-089")
@pytest.mark.parametrize("bad", ["binance:BTCUSDT", "binance:BTCUSDT=0", "binance:BTCUSDT=x"])
def test_a_bad_width_stops_the_daemon_naming_the_variable(bad: str) -> None:
    with pytest.raises(MissingConfiguration, match=PROFILE_BIN_WIDTHS):
        ingest_settings_from_env({**BASE, PROFILE_BIN_WIDTHS: bad})


@pytest.mark.trace("REQ-WP-089")
@pytest.mark.parametrize("bad", ["0", "30", "90", "abc", "-60"])
def test_a_block_length_that_is_not_a_whole_number_of_minutes_stops_the_daemon(bad: str) -> None:
    with pytest.raises(MissingConfiguration, match=PROFILE_BLOCK_SECONDS):
        ingest_settings_from_env({**BASE, PROFILE_BLOCK_SECONDS: bad})
