"""The one list of what the deployment ingests, and what derives from it (REQ-WP-098, spec 150)."""

from __future__ import annotations

import pytest

from channelflow.context import sources


@pytest.mark.trace("REQ-WP-098")
def test_the_series_list_names_every_market_the_deployment_ingests_with_its_type() -> None:
    assert ("binance", "BTCUSDT", "spot") in sources.SERIES
    assert ("bybit", "BTCUSDT", "perp") in sources.SERIES
    assert ("okx", "BTC-USDT-SWAP", "perp") in sources.SERIES
    for symbol in ("BTC-USDT", "ETH-USDT", "SOL-USDT"):
        assert ("okx", symbol, "spot") in sources.SERIES


@pytest.mark.trace("REQ-WP-098")
def test_the_book_symbols_of_a_venue_are_its_own_series_not_its_perpetuals() -> None:
    assert sources.book_symbols_for("binance") == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert sources.book_symbols_for("bybit") == ("BTCUSDT", "HYPEUSDT")
    assert sources.book_symbols_for("okx") == (
        "BTC-USDT",
        "BTC-USDT-SWAP",
        "ETH-USDT",
        "HYPE-USDT-SWAP",
        "SOL-USDT",
    )


@pytest.mark.trace("REQ-WP-098")
def test_the_derivative_symbols_of_a_venue_are_the_perpetuals_its_series_are_shown() -> None:
    assert sources.symbols_for("okx") == (
        "BTC-USDT-SWAP",
        "ETH-USDT-SWAP",
        "HYPE-USDT-SWAP",
        "SOL-USDT-SWAP",
    )
    assert sources.symbols_for("binance") == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert sources.symbols_for("bybit") == ("BTCUSDT", "HYPEUSDT")


@pytest.mark.trace("REQ-WP-098")
def test_each_okx_spot_series_is_shown_the_perpetual_of_its_own_pair() -> None:
    assert sources.perpetual_for("okx", "BTC-USDT") == "BTC-USDT-SWAP"
    assert sources.perpetual_for("okx", "ETH-USDT") == "ETH-USDT-SWAP"
    assert sources.perpetual_for("okx", "SOL-USDT") == "SOL-USDT-SWAP"
    assert sources.perpetual_for("okx", "BTC-USDT-SWAP") == "BTC-USDT-SWAP"


@pytest.mark.trace("REQ-WP-098")
def test_every_series_has_a_perpetual_and_that_perpetual_is_one_the_venue_polls() -> None:
    for venue, symbol, _ in sources.SERIES:
        perpetual = sources.perpetual_for(venue, symbol)
        assert perpetual is not None, (venue, symbol)
        assert perpetual in sources.symbols_for(venue), (venue, symbol, perpetual)


@pytest.mark.trace("REQ-WP-098")
def test_the_series_list_and_the_perpetual_mapping_name_the_same_series() -> None:
    assert {(v, s) for v, s, _ in sources.SERIES} == set(sources.PERPETUALS)


@pytest.mark.trace("REQ-WP-098")
def test_the_market_type_of_a_series_is_asked_by_venue_and_symbol() -> None:
    assert sources.market_type_of("binance", "BTCUSDT") == "spot"
    assert sources.market_type_of("okx", "BTC-USDT") == "spot"
    assert sources.market_type_of("okx", "BTC-USDT-SWAP") == "perp"
    assert sources.market_type_of("bybit", "BTCUSDT") == "perp"
    with pytest.raises(KeyError):
        sources.market_type_of("kraken", "BTCUSDT")


@pytest.mark.trace("REQ-WP-099")
def test_the_series_the_dex_pools_are_shown_on_is_an_ingested_perpetual_with_derivatives() -> None:
    from channelflow.dex import hyperevm_pools

    venue, symbol = hyperevm_pools.SERIES

    assert sources.market_type_of(venue, symbol) == "perp"
    assert sources.perpetual_for(venue, symbol) == symbol


@pytest.mark.trace("REQ-WP-099")
def test_hype_is_a_perpetual_on_two_venues_so_its_venue_basis_has_a_consensus() -> None:
    assert ("bybit", "HYPEUSDT", "perp") in sources.SERIES
    assert ("okx", "HYPE-USDT-SWAP", "perp") in sources.SERIES
    assert sources.perpetual_for("okx", "HYPE-USDT-SWAP") == "HYPE-USDT-SWAP"
