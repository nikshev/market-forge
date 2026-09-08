"""Binance message to canonical event.

# @trace: REQ-WP-003

Pure: takes a decoded message, returns a domain model, touches no socket. That
is what lets PRD section 35.6's replay tests prove something about live
behaviour -- a recorded frame and a live one follow the same path (Principle
VII).

This module is where `event_time` is assigned, which makes it where Principle I
becomes code. Binance sends two venue-side clocks and we add a third on receipt:

* `T` -- when the trade happened at the venue. This is `event_time_ns`.
* `E` -- when the venue pushed the message. Discarded; see the specification's
  Assumptions. It measures venue-side latency, nothing requires that yet, and it
  survives in the recorded fixtures if it is ever needed.
* our receipt -- `ingest_time_ns`, and never market information (PRD section 9).

Prices arrive as strings. They are parsed straight to `Decimal`: the venue sends
strings precisely so they can be read exactly, and a float would discard that on
arrival.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from channelflow.domain import (
    BookDelta,
    BookSnapshot,
    DerivativesState,
    EventMeta,
    PriceLevel,
    TradeEvent,
)

MS_TO_NS = 1_000_000


class NormalizationError(ValueError):
    """A venue message could not be turned into a canonical event.

    Raised rather than skipped: a message the connector does not understand is
    a change at the venue, and continuing past it means reporting values from a
    format nobody checked.
    """


def _require(raw: dict[str, Any], key: str, context: str) -> Any:
    if key not in raw:
        raise NormalizationError(f"{context}: missing field {key!r} in {sorted(raw)}")
    return raw[key]


def _decimal(raw: dict[str, Any], key: str, context: str) -> Decimal:
    value = _require(raw, key, context)
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise NormalizationError(f"{context}: field {key!r} is not a number: {value!r}") from exc


def _ns(raw: dict[str, Any], key: str, context: str) -> int:
    """Venue milliseconds to nanoseconds. Exact -- never through a float."""
    value = _require(raw, key, context)
    if not isinstance(value, int):
        raise NormalizationError(f"{context}: field {key!r} is not an integer ms: {value!r}")
    return value * MS_TO_NS


def _meta(
    raw: dict[str, Any],
    *,
    venue: str,
    market_type: str,
    ingest_time_ns: int,
    event_time_key: str,
    context: str,
    sequence: int | None = None,
    source_event_id: str | None = None,
) -> EventMeta:
    return EventMeta(
        source=f"{venue}-ws",
        venue=venue,
        market_type=market_type,
        symbol=str(_require(raw, "s", context)),
        event_time_ns=_ns(raw, event_time_key, context),
        ingest_time_ns=ingest_time_ns,
        sequence=sequence,
        source_event_id=source_event_id,
    )


def _levels(rows: Any, context: str) -> tuple[PriceLevel, ...]:
    try:
        # A zero quantity is a removal, not a malformed level -- PRD section 11.1.
        return tuple(PriceLevel(price=Decimal(p), qty=Decimal(q)) for p, q in rows)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise NormalizationError(f"{context}: malformed price levels: {rows!r}") from exc


def agg_trade(
    raw: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> TradeEvent:
    """An aggregate trade. `T` is the trade time; `m` says the buyer was maker."""
    context = "aggTrade"
    aggregate_id = _require(raw, "a", context)
    price = _decimal(raw, "p", context)
    qty = _decimal(raw, "q", context)
    is_buyer_maker = bool(_require(raw, "m", context))

    return TradeEvent(
        meta=_meta(
            raw,
            venue=venue,
            market_type=market_type,
            ingest_time_ns=ingest_time_ns,
            event_time_key="T",
            context=context,
            source_event_id=str(aggregate_id),
        ),
        trade_id=str(aggregate_id),
        price=price,
        qty_base=qty,
        notional_quote=price * qty,
        # If the buyer was the maker, the aggressor was the seller.
        aggressor_side="sell" if is_buyer_maker else "buy",
        is_buyer_maker=is_buyer_maker,
    )


def trade(raw: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int) -> TradeEvent:
    """An individual trade. Same shape as an aggregate trade but keyed on `t`."""
    context = "trade"
    trade_id = _require(raw, "t", context)
    price = _decimal(raw, "p", context)
    qty = _decimal(raw, "q", context)
    is_buyer_maker = bool(_require(raw, "m", context))

    return TradeEvent(
        meta=_meta(
            raw,
            venue=venue,
            market_type=market_type,
            ingest_time_ns=ingest_time_ns,
            event_time_key="T",
            context=context,
            source_event_id=str(trade_id),
        ),
        trade_id=str(trade_id),
        price=price,
        qty_base=qty,
        notional_quote=price * qty,
        aggressor_side="sell" if is_buyer_maker else "buy",
        is_buyer_maker=is_buyer_maker,
    )


def depth_update(
    raw: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> BookDelta:
    """An incremental book update. `U`..`u` is the sequence range it covers."""
    context = "depthUpdate"
    final_update_id = int(_require(raw, "u", context))

    return BookDelta(
        meta=_meta(
            raw,
            venue=venue,
            market_type=market_type,
            ingest_time_ns=ingest_time_ns,
            event_time_key="E",
            context=context,
            sequence=final_update_id,
        ),
        first_update_id=int(_require(raw, "U", context)),
        final_update_id=final_update_id,
        # Futures carry `pu`, the previous stream's final id. Spot does not.
        prev_update_id=int(raw["pu"]) if "pu" in raw else None,
        bids=_levels(_require(raw, "b", context), context),
        asks=_levels(_require(raw, "a", context), context),
    )


def depth_snapshot(
    raw: dict[str, Any],
    *,
    venue: str,
    market_type: str,
    symbol: str,
    ingest_time_ns: int,
) -> BookSnapshot:
    """A REST book snapshot. It carries no timestamp, so receipt is used for
    both clocks -- and that is stated here rather than left to be discovered."""
    context = "depthSnapshot"
    return BookSnapshot(
        meta=EventMeta(
            source=f"{venue}-rest",
            venue=venue,
            market_type=market_type,
            symbol=symbol,
            event_time_ns=ingest_time_ns,
            ingest_time_ns=ingest_time_ns,
            sequence=int(_require(raw, "lastUpdateId", context)),
            source_event_id=None,
        ),
        update_id=int(_require(raw, "lastUpdateId", context)),
        bids=_levels(_require(raw, "bids", context), context),
        asks=_levels(_require(raw, "asks", context), context),
    )


def derivatives_state(
    premium_index: dict[str, Any],
    open_interest: dict[str, Any],
    *,
    venue: str,
    ingest_time_ns: int,
) -> DerivativesState:
    """Mark price, index price, funding and open interest, from REST.

    REST rather than websocket because the futures streams carrying these are
    unreachable from this network -- established by probing, recorded in the
    specification's Assumptions.
    """
    context = "premiumIndex"
    return DerivativesState(
        meta=EventMeta(
            source=f"{venue}-rest",
            venue=venue,
            market_type="perp",
            symbol=str(_require(premium_index, "symbol", context)),
            event_time_ns=_ns(premium_index, "time", context),
            ingest_time_ns=ingest_time_ns,
            sequence=None,
            source_event_id=None,
        ),
        mark_price=_decimal(premium_index, "markPrice", context),
        index_price=_decimal(premium_index, "indexPrice", context),
        funding_rate=float(_require(premium_index, "lastFundingRate", context)),
        next_funding_time_ns=_ns(premium_index, "nextFundingTime", context),
        open_interest_base=float(_require(open_interest, "openInterest", "openInterest")),
    )
