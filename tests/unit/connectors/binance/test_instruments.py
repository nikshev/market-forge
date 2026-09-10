"""A venue payload becomes instrument values (REQ-WP-021)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.connectors.binance import instruments_from
from channelflow.domain import InstrumentRejected


def entry(symbol: str = "BTCUSDT", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": symbol,
        "status": "TRADING",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "contractSize": "1",
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
            {"filterType": "MIN_NOTIONAL", "notional": "5"},
        ],
    }
    payload.update(overrides)
    return payload


@pytest.mark.trace("REQ-WP-021")
def test_every_entry_becomes_one_instrument() -> None:
    found = instruments_from(
        {"symbols": [entry("BTCUSDT"), entry("ETHUSDT")]}, venue="binance", market_type="perp"
    )

    assert [i.symbol for i in found] == ["BTCUSDT", "ETHUSDT"]
    assert all(i.venue == "binance" and i.market_type == "perp" for i in found)


@pytest.mark.trace("REQ-WP-021")
def test_the_venue_s_field_names_stop_at_the_boundary() -> None:
    """`tickSize` inside a `PRICE_FILTER` is Binance's way of saying it. The rest
    of the system should never have to know that, which is the same reason
    REQ-WP-003 normalizes everything else here."""
    instrument = instruments_from({"symbols": [entry()]}, venue="binance", market_type="perp")[0]

    assert instrument.tick_size == Decimal("0.10")
    assert instrument.step_size == Decimal("0.001")
    assert instrument.min_notional == Decimal("5")


@pytest.mark.trace("REQ-WP-021")
def test_numbers_arrive_as_strings_and_stay_decimal() -> None:
    """Binance sends them as strings, and that is a gift: parsing "0.10" as a
    float would give a tick size the venue does not have."""
    instrument = instruments_from(
        {"symbols": [entry(tickSizeIsIrrelevant=None)]}, venue="binance", market_type="perp"
    )[0]

    assert isinstance(instrument.tick_size, Decimal)
    assert instrument.tick_size == Decimal("0.10")


@pytest.mark.trace("REQ-WP-021")
def test_a_missing_filter_is_refused_naming_the_symbol_and_the_field() -> None:
    """A tick size guessed at is worse than one absent: absent stops a
    calculation, a guess produces a number that looks like a measurement."""
    broken = entry("ETHUSDT")
    broken["filters"] = [f for f in broken["filters"] if f["filterType"] != "PRICE_FILTER"]  # type: ignore[union-attr,index]

    # "missing" specifically. Defaulting the rule to zero also raises -- the
    # value object refuses it -- but reports "tick_size is 0", and a reader would
    # go looking for a zero in the payload that is not there. Missing and zero
    # are different facts, and the mutation sweep found the test could not tell
    # them apart.
    with pytest.raises(InstrumentRejected, match="ETHUSDT: tick_size is missing"):
        instruments_from({"symbols": [broken]}, venue="binance", market_type="perp")


@pytest.mark.trace("REQ-WP-021")
def test_a_float_in_the_payload_is_refused_rather_than_converted() -> None:
    """`Decimal(0.1)` is not refused by Python and is not the venue's tick size.

    Binance sends strings, so a float here means something upstream already
    parsed the payload as JSON with float numbers -- and converting it would
    carry the binary approximation forward looking exactly like a real rule.
    """
    with pytest.raises(InstrumentRejected, match="tick_size is a float"):
        instruments_from(
            {
                "symbols": [
                    entry(
                        filters=[
                            {"filterType": "PRICE_FILTER", "tickSize": 0.1},
                            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                            {"filterType": "MIN_NOTIONAL", "notional": "5"},
                        ]
                    )
                ]
            },
            venue="binance",
            market_type="perp",
        )


@pytest.mark.trace("REQ-WP-021")
def test_a_spot_entry_has_no_contract_size() -> None:
    spot = entry()
    del spot["contractSize"]

    instrument = instruments_from({"symbols": [spot]}, venue="binance", market_type="spot")[0]

    assert instrument.contract_size is None


@pytest.mark.trace("REQ-WP-021")
def test_a_repeated_symbol_keeps_the_later_entry() -> None:
    """Stated rather than left to whichever data structure the implementation
    reaches for."""
    first = entry("BTCUSDT")
    second = entry("BTCUSDT")
    second["filters"] = [
        {"filterType": "PRICE_FILTER", "tickSize": "0.50"},
        {"filterType": "LOT_SIZE", "stepSize": "0.001"},
        {"filterType": "MIN_NOTIONAL", "notional": "5"},
    ]

    found = instruments_from({"symbols": [first, second]}, venue="binance", market_type="perp")

    assert len(found) == 1
    assert found[0].tick_size == Decimal("0.50")


@pytest.mark.trace("REQ-WP-021")
def test_a_payload_with_no_symbols_is_refused() -> None:
    """An empty result would read as "this venue lists nothing", which is a
    claim about the venue rather than about the payload."""
    with pytest.raises(InstrumentRejected, match="no instruments"):
        instruments_from({"symbols": []}, venue="binance", market_type="perp")
