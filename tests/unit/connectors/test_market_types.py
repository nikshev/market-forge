"""The market type of each venue's feed is the venue's, and agrees with the endpoint (REQ-WP-081).

The Binance daemon connects to `stream.binance.com:9443`, Binance's **spot** stream; Bybit's to
`/v5/public/linear` (perpetuals); OKX's to the v5 public socket where the *instrument* decides.
PRD §26.1's example alert says "Binance Perp"; this deployment's Binance data is not. A constant per
venue would be right for two venues and wrong for OKX the day its instrument stops being a swap, so
the
type is a function of the symbol and the test below ties it to the endpoint actually used.
"""

from __future__ import annotations

import pytest

from channelflow.connectors.venue import VENUE_REGISTRY
from channelflow.connectors.websocket import binance_stream_url

#: What an endpoint says about the market behind it. A table, so that an endpoint changing to one
#: that
#: implies another type fails the test that reads it, instead of quietly mislabelling a market.
ENDPOINT_IMPLIES = (
    # With the scheme: "stream.binance.com" is a substring of "fstream.binance.com", and the first
    # version of this table read the futures endpoint as spot.
    ("wss://stream.binance.com", "spot"),
    ("wss://fstream.binance.com", "perp"),
    ("/v5/public/linear", "perp"),
    ("/v5/public/spot", "spot"),
)


def _implied(url: str) -> str | None:
    for marker, market_type in ENDPOINT_IMPLIES:
        if marker in url:
            return market_type
    return None


@pytest.mark.trace("REQ-WP-081")
def test_every_venue_in_the_registry_names_a_market_type() -> None:
    """SC-004: none lacks one."""
    missing = [name for name, config in VENUE_REGISTRY.items() if not callable(config.market_type)]

    assert missing == []


@pytest.mark.trace("REQ-WP-081")
def test_binance_is_spot_because_its_stream_is_the_spot_stream() -> None:
    url = binance_stream_url(["btcusdt@aggTrade"])

    assert _implied(url) == "spot"
    assert VENUE_REGISTRY["binance"].market_type("BTCUSDT") == "spot"


@pytest.mark.trace("REQ-WP-081")
def test_bybit_is_perp_because_its_endpoint_is_the_linear_one() -> None:
    url = VENUE_REGISTRY["bybit"].url

    assert url is not None and _implied(url) == "perp"
    assert VENUE_REGISTRY["bybit"].market_type("BTCUSDT") == "perp"


@pytest.mark.trace("REQ-WP-081")
@pytest.mark.parametrize(
    ("symbol", "expected"),
    [("BTC-USDT-SWAP", "perp"), ("ETH-USDT-SWAP", "perp"), ("BTC-USDT", "spot")],
)
def test_okx_reads_its_instrument_not_its_venue(symbol: str, expected: str) -> None:
    assert VENUE_REGISTRY["okx"].market_type(symbol) == expected


@pytest.mark.trace("REQ-WP-081")
@pytest.mark.parametrize("symbol", ["BTC-USDT-240329", "BTCUSDT", "", "BTC-USDT-SWAP-X"])
def test_okx_refuses_an_instrument_it_does_not_recognise_rather_than_guess(symbol: str) -> None:
    """A guess is a label on the first screen that nobody checked."""
    with pytest.raises(ValueError, match="okx"):
        VENUE_REGISTRY["okx"].market_type(symbol)


@pytest.mark.trace("REQ-WP-081")
def test_the_endpoint_table_would_notice_a_futures_binance() -> None:
    """The guard on the guard: if Binance's URL became the futures one, the table says perp, and the
    test above would fail until the type was reconsidered."""
    assert _implied("wss://fstream.binance.com/stream?streams=x") == "perp"
    assert _implied("wss://stream.binance.com:9443/stream?streams=x") == "spot"
