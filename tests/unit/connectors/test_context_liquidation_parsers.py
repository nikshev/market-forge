"""What each venue's liquidation frame means (REQ-WP-094 spec 146).

The side of a liquidation is the side of the POSITION that was closed. Binance and OKX publish the
closing ORDER's side, so a SELL liquidates a long; Bybit publishes the liquidated position's side,
so
a Buy is a long. Getting one backwards flips the sign of every number downstream and is invisible in
a chart, so each venue's mapping is pinned here from a frame.

Where a frame was recorded from the venue it is in `tests/fixtures/context/`; where the venue was
silent for the whole recording window (Bybit's BTC/ETH/SOL liquidations are rare) the frame is the
one the venue's documentation shows and the test says so by its name.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.connectors.binance import liquidation as binance
from channelflow.connectors.bybit import liquidation as bybit
from channelflow.connectors.okx import liquidation as okx

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "context"
MS = 1_000_000


def recorded(name: str) -> list[dict[str, Any]]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


# --- Binance ------------------------------------------------------------------------------------


def binance_frame(**order: Any) -> dict[str, Any]:
    base = {
        "s": "BTCUSDT",
        "S": "SELL",
        "o": "LIMIT",
        "f": "IOC",
        "q": "0.014",
        "p": "9910",
        "ap": "9915.5",
        "X": "FILLED",
        "l": "0.014",
        "z": "0.012",
        "T": 1_568_014_460_893,
    }
    return {"e": "forceOrder", "E": 1_568_014_460_900, "o": {**base, **order}}


@pytest.mark.trace("REQ-WP-094")
def test_binance_a_forced_sell_is_a_long_that_was_liquidated() -> None:
    (event,) = binance.liquidation_events(binance_frame(S="SELL"), ingest_time_ns=9)
    assert event.side == "long_liquidated"


@pytest.mark.trace("REQ-WP-094")
def test_binance_a_forced_buy_is_a_short_that_was_liquidated() -> None:
    (event,) = binance.liquidation_events(binance_frame(S="BUY"), ingest_time_ns=9)
    assert event.side == "short_liquidated"


@pytest.mark.trace("REQ-WP-094")
def test_binance_event_is_the_filled_quantity_at_the_average_price_at_the_venues_time() -> None:
    (event,) = binance.liquidation_events(binance_frame(), ingest_time_ns=9)

    assert event.meta.event_time_ns == 1_568_014_460_893 * MS
    assert event.meta.ingest_time_ns == 9
    assert event.meta.venue == "binance" and event.meta.market_type == "perp"
    assert event.meta.symbol == "BTCUSDT" and event.meta.source == "binance-ws-liquidation"
    assert event.price == Decimal("9915.5")  # the average fill, not the order's limit price
    assert event.qty == Decimal("0.012")  # what was filled, not what was asked for
    assert event.notional_usd == Decimal("9915.5") * Decimal("0.012")


@pytest.mark.trace("REQ-WP-094")
def test_binance_falls_back_to_the_order_price_and_quantity_when_nothing_filled_is_reported() -> (
    None
):
    (event,) = binance.liquidation_events(binance_frame(ap="0", z="0"), ingest_time_ns=9)
    assert event.price == Decimal("9910") and event.qty == Decimal("0.014")


@pytest.mark.trace("REQ-WP-094")
def test_binance_a_recorded_frame_parses() -> None:
    frames = recorded("ws3_binance_market_forceOrder_all")
    assert frames
    for frame in frames:
        (event,) = binance.liquidation_events(frame, ingest_time_ns=1)
        assert event.meta.symbol == frame["o"]["s"]
        assert event.side == (
            "long_liquidated" if frame["o"]["S"] == "SELL" else "short_liquidated"
        )
        assert event.notional_usd == event.price * event.qty


@pytest.mark.trace("REQ-WP-094")
def test_binance_only_the_symbols_asked_for_are_returned() -> None:
    frame = binance_frame(s="ETHUSDT")
    assert binance.liquidation_events(frame, ingest_time_ns=1, symbols={"BTCUSDT"}) == []
    assert len(binance.liquidation_events(frame, ingest_time_ns=1, symbols={"ETHUSDT"})) == 1


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize(
    "frame",
    [{"result": None, "id": 1}, {"e": "markPriceUpdate", "s": "BTCUSDT"}, {}],
)
def test_binance_frames_that_are_not_liquidations_are_ignored_not_errors(
    frame: dict[str, Any],
) -> None:
    assert binance.liquidation_events(frame, ingest_time_ns=1) == []


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize(
    "order",
    [{"S": "SIDEWAYS"}, {"ap": "0", "p": "0"}, {"z": "0", "q": "0", "l": "0"}, {"T": "x"}],
)
def test_binance_a_frame_that_cannot_be_read_is_refused_with_a_reason(
    order: dict[str, Any],
) -> None:
    with pytest.raises(binance.LiquidationRefused):
        binance.liquidation_events(binance_frame(**order), ingest_time_ns=1)


# --- Bybit --------------------------------------------------------------------------------------


def bybit_frame_documented(**row: Any) -> dict[str, Any]:
    """The frame Bybit's documentation shows for `allLiquidation`; no liquidation of the symbols
    watched arrived in the recording window, so this one is documented, not recorded."""
    base = {"T": 1_739_502_302_929, "s": "BTCUSDT", "S": "Buy", "v": "20000", "p": "0.04499"}
    return {
        "topic": "allLiquidation.BTCUSDT",
        "type": "snapshot",
        "ts": 1_739_502_303_204,
        "data": [{**base, **row}],
    }


@pytest.mark.trace("REQ-WP-094")
def test_bybit_a_buy_update_is_a_long_that_was_liquidated() -> None:
    """Bybit documents the field as the position's side: 'a Buy update means a long position has
    been liquidated' -- the opposite convention from Binance's order side."""
    (event,) = bybit.liquidation_events(bybit_frame_documented(S="Buy"), ingest_time_ns=9)
    assert event.side == "long_liquidated"


@pytest.mark.trace("REQ-WP-094")
def test_bybit_a_sell_update_is_a_short_that_was_liquidated() -> None:
    (event,) = bybit.liquidation_events(bybit_frame_documented(S="Sell"), ingest_time_ns=9)
    assert event.side == "short_liquidated"


@pytest.mark.trace("REQ-WP-094")
def test_bybit_event_fields_and_times() -> None:
    (event,) = bybit.liquidation_events(bybit_frame_documented(), ingest_time_ns=9)

    assert event.meta.event_time_ns == 1_739_502_302_929 * MS
    assert event.meta.ingest_time_ns == 9
    assert event.meta.venue == "bybit" and event.meta.market_type == "perp"
    assert event.meta.source == "bybit-ws-liquidation"
    assert event.price == Decimal("0.04499") and event.qty == Decimal("20000")
    assert event.notional_usd == Decimal("0.04499") * Decimal("20000")


@pytest.mark.trace("REQ-WP-094")
def test_bybit_a_frame_with_several_events_gives_several() -> None:
    frame = bybit_frame_documented()
    frame["data"] = frame["data"] + [dict(frame["data"][0], S="Sell", T=1_739_502_302_999)]
    events = bybit.liquidation_events(frame, ingest_time_ns=1)
    assert [e.side for e in events] == ["long_liquidated", "short_liquidated"]


@pytest.mark.trace("REQ-WP-094")
def test_bybit_subscription_acknowledgements_and_other_topics_are_ignored() -> None:
    ack = recorded("ws_bybit_allLiquidation")[0]
    assert bybit.liquidation_events(ack, ingest_time_ns=1) == []
    assert (
        bybit.liquidation_events({"topic": "tickers.BTCUSDT", "data": {}}, ingest_time_ns=1) == []
    )


@pytest.mark.trace("REQ-WP-094")
def test_bybit_only_the_symbols_asked_for_are_returned() -> None:
    frame = bybit_frame_documented(s="ETHUSDT")
    assert bybit.liquidation_events(frame, ingest_time_ns=1, symbols={"BTCUSDT"}) == []


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize("row", [{"S": "Hold"}, {"p": "0"}, {"v": "-1"}, {"T": "x"}])
def test_bybit_a_row_that_cannot_be_read_is_refused_with_a_reason(row: dict[str, Any]) -> None:
    with pytest.raises(bybit.LiquidationRefused):
        bybit.liquidation_events(bybit_frame_documented(**row), ingest_time_ns=1)


# --- OKX ----------------------------------------------------------------------------------------

CT_VAL = {"MAGIC-USDT-SWAP": Decimal("10"), "BTC-USDT-SWAP": Decimal("0.01")}


def okx_frame(**detail: Any) -> dict[str, Any]:
    base = {
        "bkLoss": "0",
        "bkPx": "0.12663",
        "ccy": "",
        "posSide": "long",
        "side": "sell",
        "sz": "1560",
        "ts": "1791709657204",
    }
    return {
        "arg": {"channel": "liquidation-orders", "instType": "SWAP"},
        "data": [
            {
                "details": [{**base, **detail}],
                "instFamily": "MAGIC-USDT",
                "instId": "MAGIC-USDT-SWAP",
                "instType": "SWAP",
                "uly": "MAGIC-USDT",
            }
        ],
    }


@pytest.mark.trace("REQ-WP-094")
def test_okx_a_closing_sell_of_a_long_position_is_a_long_that_was_liquidated() -> None:
    """The recorded frame: posSide=long, side=sell."""
    (event,) = okx.liquidation_events(okx_frame(), ingest_time_ns=9, contract_values=CT_VAL)
    assert event.side == "long_liquidated"


@pytest.mark.trace("REQ-WP-094")
def test_okx_a_closing_buy_of_a_short_position_is_a_short_that_was_liquidated() -> None:
    (event,) = okx.liquidation_events(
        okx_frame(posSide="short", side="buy"), ingest_time_ns=9, contract_values=CT_VAL
    )
    assert event.side == "short_liquidated"


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize(
    ("pos_side", "side", "expected"),
    [("net", "sell", "long_liquidated"), ("net", "buy", "short_liquidated")],
)
def test_okx_in_net_mode_the_closing_orders_side_gives_the_position(
    pos_side: str, side: str, expected: str
) -> None:
    (event,) = okx.liquidation_events(
        okx_frame(posSide=pos_side, side=side), ingest_time_ns=9, contract_values=CT_VAL
    )
    assert event.side == expected


@pytest.mark.trace("REQ-WP-094")
def test_okx_a_combination_that_contradicts_itself_is_unknown_not_guessed() -> None:
    (event,) = okx.liquidation_events(
        okx_frame(posSide="long", side="buy"), ingest_time_ns=9, contract_values=CT_VAL
    )
    assert event.side == "unknown"


@pytest.mark.trace("REQ-WP-094")
def test_okx_size_is_contracts_and_is_converted_to_base_units() -> None:
    (event,) = okx.liquidation_events(okx_frame(), ingest_time_ns=9, contract_values=CT_VAL)

    assert event.qty == Decimal("1560") * Decimal("10")
    assert event.price == Decimal("0.12663")
    assert event.notional_usd == event.price * event.qty
    assert event.meta.event_time_ns == 1_791_709_657_204 * MS
    assert event.meta.symbol == "MAGIC-USDT-SWAP" and event.meta.source == "okx-ws-liquidation"


@pytest.mark.trace("REQ-WP-094")
def test_okx_a_contract_size_we_do_not_know_refuses_the_event_rather_than_guessing() -> None:
    with pytest.raises(okx.LiquidationRefused, match="MAGIC-USDT-SWAP"):
        okx.liquidation_events(
            okx_frame(), ingest_time_ns=9, contract_values={"MAGIC-USDT-SWAP": None}
        )


@pytest.mark.trace("REQ-WP-094")
def test_okx_every_recorded_frame_for_a_watched_instrument_parses() -> None:
    parsed = 0
    for frame in recorded("ws_okx_liquidation"):
        for event in okx.liquidation_events(frame, ingest_time_ns=1, contract_values=CT_VAL):
            assert event.side == "long_liquidated"
            parsed += 1
    assert parsed >= 1


@pytest.mark.trace("REQ-WP-094")
def test_okx_instruments_not_watched_are_ignored() -> None:
    assert (
        okx.liquidation_events(
            okx_frame(), ingest_time_ns=1, contract_values={"BTC-USDT-SWAP": Decimal("0.01")}
        )
        == []
    )


@pytest.mark.trace("REQ-WP-094")
def test_okx_acknowledgements_and_other_channels_are_ignored() -> None:
    ack = recorded("ws_okx_liquidation")[0]
    assert okx.liquidation_events(ack, ingest_time_ns=1, contract_values=CT_VAL) == []
    # Another channel's frame that happens to carry a watched instrument's liquidation-shaped data.
    other = {"arg": {"channel": "trades"}, "data": okx_frame()["data"]}
    assert okx.liquidation_events(other, ingest_time_ns=1, contract_values=CT_VAL) == []


@pytest.mark.trace("REQ-WP-094")
@pytest.mark.parametrize("detail", [{"bkPx": "0"}, {"sz": "0"}, {"ts": "x"}, {"sz": ""}])
def test_okx_a_detail_that_cannot_be_read_is_refused_with_a_reason(detail: dict[str, Any]) -> None:
    with pytest.raises(okx.LiquidationRefused):
        okx.liquidation_events(okx_frame(**detail), ingest_time_ns=1, contract_values=CT_VAL)
