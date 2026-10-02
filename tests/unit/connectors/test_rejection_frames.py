"""Reading a venue's refusal, pinned to frames the venues actually sent (REQ-WP-078).

# @trace: REQ-WP-078

Both frames below were captured live on 2026-10-02 by subscribing to something that does
not exist. Neither is written from documentation: the repository's rule since ADR-004 is
that a fixture is what the venue sent, and a parser tested against an invented frame
proves that the parser agrees with its author.

Binance has no rule. Its combined-stream endpoint is recorded here as having answered a
malformed stream name -- upper case -- by connecting and delivering nothing, so there is no
refusal frame to read, and writing one from a description would be the invented frame again.
"""

from __future__ import annotations

import json

import pytest

from channelflow.connectors.venue import rejection

OKX_REFUSAL = (
    '{"event":"error","msg":"Subscribe failed, wrong URL or channel:trades,'
    "instId:trades.BTC-USDT-SWAP doesn't exist. Please use the correct URL, channel and "
    'parameters referring to API document.","code":"60018","connId":"b2b0944b"}'
)
BYBIT_REFUSAL = (
    '{"success":false,"ret_msg":"error:handler not found,topic:publicTrade.NOTASYMBOL",'
    '"conn_id":"da7tne17jutmkv5im010-bcdap","req_id":"","op":"subscribe"}'
)


@pytest.mark.trace("REQ-WP-078")
def test_okx_refusal_returns_the_venues_message() -> None:
    message = rejection("okx", OKX_REFUSAL)

    assert message is not None and message.startswith("Subscribe failed, wrong URL or channel")


@pytest.mark.trace("REQ-WP-078")
def test_bybit_refusal_returns_the_venues_message() -> None:
    assert (
        rejection("bybit", BYBIT_REFUSAL) == "error:handler not found,topic:publicTrade.NOTASYMBOL"
    )


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("venue", "frame"),
    [
        ("okx", json.dumps({"event": "subscribe", "arg": {"channel": "trades", "instId": "X"}})),
        ("okx", json.dumps({"arg": {"channel": "trades"}, "data": [{"px": "1"}]})),
        ("okx", "pong"),
        ("bybit", json.dumps({"success": True, "ret_msg": "", "op": "subscribe"})),
        ("bybit", json.dumps({"topic": "publicTrade.BTCUSDT", "data": []})),
        ("binance", json.dumps({"stream": "btcusdt@aggTrade", "data": {}})),
        ("binance", OKX_REFUSAL),  # another venue's refusal means nothing here
        ("okx", BYBIT_REFUSAL),
    ],
)
def test_a_frame_that_is_not_this_venues_refusal_is_none(venue: str, frame: str) -> None:
    assert rejection(venue, frame) is None


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("frame", ["not json at all", "[]", "42", "null", '"a string"', ""])
@pytest.mark.parametrize("venue", ["okx", "bybit", "binance"])
def test_a_frame_of_any_other_shape_is_none_and_never_raises(venue: str, frame: str) -> None:
    assert rejection(venue, frame) is None


@pytest.mark.trace("REQ-WP-078")
def test_an_unknown_venue_is_none() -> None:
    assert rejection("kraken", OKX_REFUSAL) is None
