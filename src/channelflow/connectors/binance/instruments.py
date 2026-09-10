"""Binance's instrument payload, normalized (REQ-WP-021).

# @trace: REQ-WP-021
# @trace: REQ-WP-003

`tickSize` inside a `PRICE_FILTER` is Binance's way of saying "the smallest
price increment". The rest of the system should never have to know that, which
is the same reason [[REQ-WP-003]] normalizes everything else at this boundary.

The numbers arrive as strings, and that is a gift rather than an inconvenience:
`Decimal("0.10")` is the venue's tick size and `float("0.10")` is not.

Where the payload came from is the caller's business. The rest of this connector
keeps the wire behind a `Transport` protocol and this follows it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

from channelflow.domain.instrument import Instrument, InstrumentRejected

#: Binance names each rule by the filter that carries it. One place, so a reader
#: comparing this against the venue's documentation has one thing to check.
_FILTERS = {
    "tick_size": ("PRICE_FILTER", "tickSize"),
    "step_size": ("LOT_SIZE", "stepSize"),
    "min_notional": ("MIN_NOTIONAL", "notional"),
}


def instruments_from(
    payload: Mapping[str, object], *, venue: str, market_type: str
) -> tuple[Instrument, ...]:
    """Every instrument the payload describes, in the order it described them.

    A symbol appearing twice keeps the later entry. Said out loud because it is
    otherwise decided by whichever data structure the implementation reached
    for, and a venue that repeats a symbol is describing an amendment.
    """
    entries = payload.get("symbols")
    if not isinstance(entries, Sequence) or not entries:
        raise InstrumentRejected(
            f"{venue}: the payload describes no instruments; an empty result would read "
            "as a claim about the venue rather than about the payload"
        )

    found: dict[str, Instrument] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise InstrumentRejected(
                f"{venue}: an entry is a {type(entry).__name__}, not an object"
            )
        instrument = _one(entry, venue=venue, market_type=market_type)
        found[instrument.symbol] = instrument
    return tuple(found.values())


def _one(entry: Mapping[str, object], *, venue: str, market_type: str) -> Instrument:
    symbol = str(entry.get("symbol", ""))
    filters = entry.get("filters")
    by_type: dict[str, Mapping[str, object]] = {}
    if isinstance(filters, Sequence):
        for item in filters:
            if isinstance(item, Mapping):
                by_type[str(item.get("filterType", ""))] = item

    rules: dict[str, Decimal] = {}
    for name, (filter_type, field) in _FILTERS.items():
        source = by_type.get(filter_type, {})
        if field not in source:
            raise InstrumentRejected(
                f"{symbol}: {name} is missing (no {field!r} in a {filter_type}); a rule "
                "guessed at produces a number that looks like a measurement"
            )
        rules[name] = _decimal(source[field], name=name, symbol=symbol)

    raw_contract = entry.get("contractSize")
    contract_size = (
        None
        if raw_contract is None
        else _decimal(raw_contract, name="contract_size", symbol=symbol)
    )
    return Instrument(
        venue=venue,
        symbol=symbol,
        market_type=market_type,
        base_asset=str(entry.get("baseAsset", "")),
        quote_asset=str(entry.get("quoteAsset", "")),
        contract_size=contract_size,
        status=str(entry.get("status", "")),
        **rules,
    )


def _decimal(value: object, *, name: str, symbol: str) -> Decimal:
    """A venue's string into a `Decimal`, refusing anything that is not one.

    `Decimal(float)` is not refused by Python and would quietly carry a binary
    approximation of the venue's rule, so a float is rejected here rather than
    converted.
    """
    if isinstance(value, Decimal):
        return value
    if not isinstance(value, str | int):
        raise InstrumentRejected(
            f"{symbol}: {name} is a {type(value).__name__}; a rule that went through "
            "binary floating point is not the venue's rule"
        )
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise InstrumentRejected(f"{symbol}: {name} is {value!r}, which is not a number") from exc
