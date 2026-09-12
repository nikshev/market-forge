"""Bybit v5 message to canonical event.

# @trace: REQ-WP-043

Pure: takes a decoded message, returns a domain model, touches no socket. That
is [[REQ-WP-003]]'s shape and the reason PRD section 35.6's replay tests can say
something about live behaviour -- a recorded frame and a live one follow the
same path (Principle VII).

**The taker side arrives, rather than being derived.** Binance sends `m`,
whether the *buyer* was the maker, so the aggressor is the other party. Bybit's
documentation calls `S` the taker side and sends `Buy` or `Sell` directly. Two
venues, two conventions, one canonical field -- and getting this backwards
inverts every order-flow figure built on it while showing no symptom.

**Gap detection uses `u`, not `seq`.** The orderbook documentation's prose says
to watch `seq` for discontinuities; its own field table calls `seq` a "cross
sequence" for comparing depth levels, and the two disagree. Forty consecutive
recorded messages settle it: `u` increments by exactly one every time and `seq`
jumps by between 34 and 289. This is [[ADR-004]]'s reason for recording fixtures
instead of writing them, arriving as a concrete number.

Prices arrive as strings and are parsed straight to `Decimal`: the venue sends
strings precisely so they can be read exactly, and a float would discard that on
arrival.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from channelflow.domain import (
    BookDelta,
    BookSnapshot,
    DerivativesState,
    EventMeta,
    PriceLevel,
    TradeEvent,
)

MS_TO_NS = 1_000_000

#: What Bybit's `S` means, per its own documentation: the taker's side.
_TAKER: dict[str, Literal["buy", "sell"]] = {"Buy": "buy", "Sell": "sell"}


class NormalizationError(ValueError):
    """A message that cannot be turned into a domain event.

    Raised rather than skipped: a connector that dropped what it could not read
    would report a quiet market, and a quiet market is a thing somebody trades
    on.
    """


def _require(raw: dict[str, Any], key: str, context: str) -> Any:
    if key not in raw:
        raise NormalizationError(f"{context}: no {key!r} in {sorted(raw)}")
    return raw[key]


def _decimal(raw: dict[str, Any], key: str, context: str) -> Decimal:
    try:
        return Decimal(str(_require(raw, key, context)))
    except InvalidOperation as exc:
        raise NormalizationError(f"{context}: {key!r} is not a number: {raw[key]!r}") from exc


def _levels(rows: Any, context: str) -> tuple[PriceLevel, ...]:
    if not isinstance(rows, list):
        raise NormalizationError(f"{context}: expected a list of levels, got {type(rows).__name__}")
    out: list[PriceLevel] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            raise NormalizationError(f"{context}: a level is a [price, size] pair, got {row!r}")
        out.append(PriceLevel(price=Decimal(str(row[0])), qty=Decimal(str(row[1]))))
    return tuple(out)


def public_trade(
    raw: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> TradeEvent:
    """One fill from `publicTrade.{symbol}`.

    `T` is when the order filled at the venue and is the event time. The
    envelope's `ts` is when Bybit pushed the batch; it is discarded here for the
    reason the Binance connector discards `E` -- it measures venue-side latency,
    nothing requires that yet, and it survives in the recorded fixtures.
    """
    context = "publicTrade"
    side = str(_require(raw, "S", context))
    if side not in _TAKER:
        raise NormalizationError(f"{context}: unknown taker side {side!r}")

    price = _decimal(raw, "p", context)
    qty = _decimal(raw, "v", context)
    event_time_ns = int(_require(raw, "T", context)) * MS_TO_NS

    return TradeEvent(
        meta=EventMeta(
            source="bybit-ws",
            venue=venue,
            market_type=market_type,
            symbol=str(_require(raw, "s", context)),
            event_time_ns=event_time_ns,
            ingest_time_ns=ingest_time_ns,
            sequence=int(raw["seq"]) if "seq" in raw else None,
            source_event_id=str(_require(raw, "i", context)),
        ),
        trade_id=str(_require(raw, "i", context)),
        price=price,
        qty_base=qty,
        notional_quote=price * qty,
        aggressor_side=_TAKER[side],
        # Bybit names the taker, so the buyer was the maker exactly when the
        # taker was the seller. Derived here rather than left absent: the field
        # is knowable from what the venue sent, and an absent value would make
        # this venue look like one that does not publish the flag.
        is_buyer_maker=side == "Sell",
    )


def order_book_message(
    message: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> BookSnapshot | BookDelta:
    """A message from `orderbook.{depth}.{symbol}`, snapshot or delta.

    One function for both because the venue sends them on one topic and
    distinguishes them by a field. A caller that had to know which it was about
    to receive would be reimplementing the dispatch the venue already did.
    """
    context = "orderbook"
    kind = str(_require(message, "type", context))
    data = _require(message, "data", context)
    if not isinstance(data, dict):
        raise NormalizationError(f"{context}: expected an object in 'data'")

    symbol = str(_require(data, "s", context))
    update_id = int(_require(data, "u", context))
    # `cts` is the matching-engine timestamp that correlates with public
    # trades; the envelope's `ts` is the push time. The first is market
    # information and the second is not, so the first is the event time.
    event_time_ns = int(_require(message, "cts", context)) * MS_TO_NS
    meta = EventMeta(
        source="bybit-ws",
        venue=venue,
        market_type=market_type,
        symbol=symbol,
        event_time_ns=event_time_ns,
        ingest_time_ns=ingest_time_ns,
        sequence=update_id,
        source_event_id=None,
    )
    bids = _levels(_require(data, "b", context), context)
    asks = _levels(_require(data, "a", context), context)

    if kind == "snapshot":
        return BookSnapshot(meta=meta, update_id=update_id, bids=bids, asks=asks)
    if kind == "delta":
        return BookDelta(
            meta=meta,
            # Bybit sends one id per message rather than a range, and `u`
            # increments by one: the first and final id of a delta are the same
            # number. Stated rather than left as a coincidence -- a reader who
            # assumed a Binance-style range would look for a gap that cannot
            # appear here.
            first_update_id=update_id,
            final_update_id=update_id,
            prev_update_id=update_id - 1,
            bids=bids,
            asks=asks,
        )
    raise NormalizationError(f"{context}: unknown message type {kind!r}")


def rest_order_book(
    raw: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> BookSnapshot:
    """A REST book snapshot from `/v5/market/orderbook`.

    It carries `ts`, the venue's own timestamp, so unlike the Binance REST
    snapshot this has a real event time and does not have to borrow receipt.
    """
    context = "restOrderbook"
    result = _require(raw, "result", context)
    if not isinstance(result, dict):
        raise NormalizationError(f"{context}: expected an object in 'result'")

    return BookSnapshot(
        meta=EventMeta(
            source="bybit-rest",
            venue=venue,
            market_type=market_type,
            symbol=str(_require(result, "s", context)),
            event_time_ns=int(_require(result, "ts", context)) * MS_TO_NS,
            ingest_time_ns=ingest_time_ns,
            sequence=int(_require(result, "u", context)),
            source_event_id=None,
        ),
        update_id=int(_require(result, "u", context)),
        bids=_levels(_require(result, "b", context), context),
        asks=_levels(_require(result, "a", context), context),
    )


def derivatives_state(
    ticker: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> DerivativesState:
    """Funding, open interest, mark and index, from one `/v5/market/tickers` row.

    One call where OKX needs four, which is worth stating because it is the
    reason a Bybit state has a single timestamp and an OKX state has a spread
    ([[REQ-WP-049]]).

    **Open interest is already in base units here.** OKX reports contracts for
    the same market, and reading its figure the way this one reads correctly
    makes OKX appear to hold fifty times Bybit's position. The comment is here
    rather than only there because this is the side that looks like it needs no
    conversion, and that is exactly why somebody would copy it.

    **`nextFundingTime` is the settlement this rate pays at.** OKX calls the
    same instant `fundingTime` and uses `nextFundingTime` for the one after, so
    the like-named fields are eight hours apart. Mapping by name would put one
    venue a settlement period out.
    """
    context = "tickers"

    def maybe(key: str) -> Decimal | None:
        value = ticker.get(key)
        return None if value in (None, "") else _decimal(ticker, key, context)

    mark = maybe("markPrice")
    index = maybe("indexPrice")
    basis_bps = None
    if mark is not None and index is not None and index != 0:
        basis_bps = float((mark / index - 1) * 10_000)

    funding = ticker.get("fundingRate")
    open_interest = maybe("openInterest")
    open_interest_value = maybe("openInterestValue")
    settlement = ticker.get("nextFundingTime")

    return DerivativesState(
        meta=EventMeta(
            source=f"{venue}-rest",
            venue=venue,
            market_type=market_type,
            symbol=str(_require(ticker, "symbol", context)),
            event_time_ns=ingest_time_ns,
            ingest_time_ns=ingest_time_ns,
            sequence=None,
            source_event_id=None,
        ),
        mark_price=mark,
        index_price=index,
        # An empty string is what this venue sends for "not applicable", and it
        # is not a rate of zero: a market in balance and a market with no
        # funding mechanism are different facts ([[REQ-WP-031]]).
        funding_rate=None if funding in (None, "") else float(funding),
        next_funding_time_ns=None if settlement in (None, "") else int(settlement) * MS_TO_NS,
        open_interest_base=None if open_interest is None else float(open_interest),
        open_interest_usd=None if open_interest_value is None else float(open_interest_value),
        basis_bps=basis_bps,
    )
