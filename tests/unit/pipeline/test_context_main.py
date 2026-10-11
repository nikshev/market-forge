"""The collector's configuration is read strictly (REQ-WP-093)."""

from __future__ import annotations

import pytest

from channelflow.pipeline import context_main as main
from channelflow.settings import MissingConfiguration


@pytest.mark.trace("REQ-WP-093")
def test_a_venue_is_required() -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_CONTEXT_VENUE"):
        main.context_settings_from_env({})


@pytest.mark.trace("REQ-WP-093")
def test_an_unknown_venue_is_refused_naming_the_known_ones() -> None:
    with pytest.raises(MissingConfiguration, match="binance, bybit, okx"):
        main.context_settings_from_env({"CHANNELFLOW_CONTEXT_VENUE": "kraken"})


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize(
    ("venue", "symbols"),
    [
        ("binance", ("BTCUSDT", "ETHUSDT", "SOLUSDT")),
        ("bybit", ("BTCUSDT",)),
        ("okx", ("BTC-USDT-SWAP",)),
    ],
)
def test_the_symbols_default_to_the_ones_the_deployment_shows(
    venue: str, symbols: tuple[str, ...]
) -> None:
    settings = main.context_settings_from_env({"CHANNELFLOW_CONTEXT_VENUE": venue})
    assert settings.symbols == symbols
    assert settings.port == main.DEFAULT_PORT


@pytest.mark.trace("REQ-WP-093")
def test_symbols_and_port_can_be_set_and_are_trimmed() -> None:
    settings = main.context_settings_from_env(
        {
            "CHANNELFLOW_CONTEXT_VENUE": " Binance ",
            "CHANNELFLOW_CONTEXT_SYMBOLS": "BTCUSDT, ETHUSDT ,",
            "CHANNELFLOW_CONTEXT_PORT": "9200",
        }
    )
    assert settings.venue == "binance"
    assert settings.symbols == ("BTCUSDT", "ETHUSDT")
    assert settings.port == 9200


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize("port", ["abc", "0", "70000", "-1"])
def test_a_bad_port_is_refused(port: str) -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_CONTEXT_PORT"):
        main.context_settings_from_env(
            {"CHANNELFLOW_CONTEXT_VENUE": "bybit", "CHANNELFLOW_CONTEXT_PORT": port}
        )


@pytest.mark.trace("REQ-WP-094")
def test_the_liquidation_stream_runs_by_default_and_can_be_turned_off() -> None:
    assert main.context_settings_from_env({"CHANNELFLOW_CONTEXT_VENUE": "okx"}).streams == (
        "liquidations",
    )
    off = main.context_settings_from_env(
        {"CHANNELFLOW_CONTEXT_VENUE": "okx", "CHANNELFLOW_CONTEXT_STREAMS": ""}
    )
    assert off.streams == ()


@pytest.mark.trace("REQ-WP-094")
def test_an_unknown_stream_is_refused_naming_the_known_ones() -> None:
    with pytest.raises(MissingConfiguration, match="liquidations"):
        main.context_settings_from_env(
            {"CHANNELFLOW_CONTEXT_VENUE": "okx", "CHANNELFLOW_CONTEXT_STREAMS": "tarot"}
        )
