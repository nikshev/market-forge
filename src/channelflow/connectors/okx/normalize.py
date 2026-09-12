"""OKX v5 message to canonical event.

# @trace: REQ-WP-044

Pure: takes a decoded message, returns a domain model, touches no socket -- the
shape [[REQ-WP-003]] established and the reason PRD section 35.6's replay tests
say anything about live behaviour.

**Size arrives in contracts, and this is the whole point of the module.**
Binance and Bybit send a quantity in the base asset. OKX sends `sz` as a number
of contracts, and `BTC-USDT-SWAP` carries `ctVal = 0.01 BTC`. A connector that
read `sz` the same way would report volumes a hundred times too large on that
instrument, and nothing downstream would show a symptom: the numbers stay
positive, ordered and plausible. The cross-venue comparison this phase exists
for would then read a hundredfold difference as a finding.

The contract value is therefore an argument, taken from the venue's own
instrument data. Not a constant: it differs per instrument and can change, and a
compiled-in number would be right until the day it silently was not.

**What `side` means was measured, not assumed.** OKX's field table does not
render through any fetchable documentation page, so it was established from 158
interleaved recorded messages: trades marked `buy` executed at or above the ask
25 times out of 26, and trades marked `sell` executed at or below the bid 91
times out of 91. That is the signature of the **taker's** side -- a taker buying
lifts the ask, a taker selling hits the bid. The single exception is a trade
that arrived before the book delta that had already moved the price, which is
what an interleaved recording looks like and not a counter-example.

A test over the committed fixtures asserts this, because a test fails when the
venue changes and a sentence in a docstring does not.
"""

from __future__ import annotations

from dataclasses import dataclass
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

#: Measured from recorded traffic; see the module docstring.
_TAKER: dict[str, Literal["buy", "sell"]] = {"buy": "buy", "sell": "sell"}

#: What a snapshot's `prevSeqId` carries: there is nothing before it.
NO_PREDECESSOR = -1


class NormalizationError(ValueError):
    """A message that cannot be turned into a domain event.

    Raised rather than skipped: a connector that dropped what it could not read
    would report a quiet market, and a quiet market is a thing somebody trades
    on.
    """


class UnknownContractValue(NormalizationError):
    """An instrument whose contract value nobody supplied.

    Refused rather than defaulted to one. A default of one contract per base
    unit is right for some instruments and a hundredfold error on others, and
    the error has no symptom.
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
            raise NormalizationError(f"{context}: a level is a [price, size, ...] row, got {row!r}")
        out.append(PriceLevel(price=Decimal(str(row[0])), qty=Decimal(str(row[1]))))
    return tuple(out)


def contract_value(instruments: dict[str, Any], *, inst_id: str) -> Decimal:
    """How much of the base asset one contract is, from the venue's own data.

    Read rather than assumed. `BTC-USDT-SWAP` is `0.01 BTC`; another instrument
    is another number; the same instrument can be redenominated.
    """
    context = "instruments"
    rows = _require(instruments, "data", context)
    for row in rows:
        if row.get("instId") == inst_id:
            if row.get("ctValCcy") and row.get("ctVal"):
                return _decimal(row, "ctVal", context)
            raise UnknownContractValue(f"{inst_id} reports no contract value")
    raise UnknownContractValue(f"{inst_id} is not in this instruments response")


def public_trade(
    raw: dict[str, Any],
    *,
    venue: str,
    market_type: str,
    contract_value: Decimal,
    ingest_time_ns: int,
) -> TradeEvent:
    """One fill from the `trades` channel, with size converted to base units."""
    context = "trades"
    side = str(_require(raw, "side", context))
    if side not in _TAKER:
        raise NormalizationError(f"{context}: unknown taker side {side!r}")
    if contract_value <= 0:
        raise UnknownContractValue(
            f"{context}: a contract worth {contract_value} of the base asset describes nothing"
        )

    price = _decimal(raw, "px", context)
    contracts = _decimal(raw, "sz", context)
    # The conversion this module exists for.
    qty_base = contracts * contract_value

    return TradeEvent(
        meta=EventMeta(
            source="okx-ws",
            venue=venue,
            market_type=market_type,
            symbol=str(_require(raw, "instId", context)),
            event_time_ns=int(_require(raw, "ts", context)) * MS_TO_NS,
            ingest_time_ns=ingest_time_ns,
            sequence=int(raw["seqId"]) if "seqId" in raw else None,
            source_event_id=str(_require(raw, "tradeId", context)),
        ),
        trade_id=str(_require(raw, "tradeId", context)),
        price=price,
        qty_base=qty_base,
        notional_quote=price * qty_base,
        aggressor_side=_TAKER[side],
        # OKX names the taker, so the buyer was the maker exactly when the taker
        # was the seller.
        is_buyer_maker=side == "sell",
    )


def order_book_message(
    message: dict[str, Any], *, venue: str, market_type: str, ingest_time_ns: int
) -> BookSnapshot | BookDelta:
    """A message from the `books` channel, snapshot or update.

    OKX carries an explicit chain: every message's `prevSeqId` is the previous
    message's `seqId`, and a snapshot's is `-1`. That is a stronger statement
    than either neighbour venue makes -- Binance sends a range and Bybit a
    single incrementing id -- and it means a gap is detectable without
    remembering what came before.
    """
    context = "books"
    action = str(_require(message, "action", context))
    rows = _require(message, "data", context)
    if not rows:
        raise NormalizationError(f"{context}: a message with no data describes nothing")
    data = rows[0]

    seq_id = int(_require(data, "seqId", context))
    prev_seq_id = int(_require(data, "prevSeqId", context))
    meta = EventMeta(
        source="okx-ws",
        venue=venue,
        market_type=market_type,
        symbol=str(_require(message["arg"], "instId", context)),
        event_time_ns=int(_require(data, "ts", context)) * MS_TO_NS,
        ingest_time_ns=ingest_time_ns,
        sequence=seq_id,
        source_event_id=None,
    )
    bids = _levels(_require(data, "bids", context), context)
    asks = _levels(_require(data, "asks", context), context)

    if action == "snapshot":
        return BookSnapshot(meta=meta, update_id=seq_id, bids=bids, asks=asks)
    if action == "update":
        return BookDelta(
            meta=meta,
            first_update_id=seq_id,
            final_update_id=seq_id,
            # The venue says what came before rather than leaving it to be
            # inferred; `-1` on a snapshot means nothing did.
            prev_update_id=None if prev_seq_id == NO_PREDECESSOR else prev_seq_id,
            bids=bids,
            asks=asks,
        )
    raise NormalizationError(f"{context}: unknown action {action!r}")


class StaleAssembly(NormalizationError):
    """The readings this state was assembled from are too far apart.

    OKX publishes funding, open interest, mark and index from four endpoints
    with four timestamps, so a state is never a snapshot -- it is four readings
    stitched together. Across a fast move, a mark from one second and an index
    from the next produce a basis that neither moment had.
    """


@dataclass(frozen=True)
class AssembledDerivatives:
    """A state, and how far apart the readings behind it were taken.

    The spread is carried rather than discarded because it is the only thing
    that distinguishes a state assembled in fifty milliseconds from one
    assembled across a rate-limit pause. Bybit needs none of this: one call,
    one timestamp.
    """

    state: DerivativesState
    oldest_ns: int
    newest_ns: int

    @property
    def spread_ns(self) -> int:
        return self.newest_ns - self.oldest_ns


def open_interest_base(open_interest: dict[str, Any], *, contract_value: Decimal) -> Decimal:
    """Open interest in base units, from a figure the venue quotes in contracts.

    **`oi` is contracts.** `BTC-USDT-SWAP` carries `ctVal = 0.01 BTC`, so
    reading `oi` as a base quantity overstates it a hundredfold -- and measured
    against Bybit on 2026-09-12, that makes OKX appear to hold 51.5 times
    Bybit's open interest where it actually holds 0.52 times. Positive, ordered,
    believable, and a finding somebody would report.

    The venue also publishes `oiCcy`, already in base units, and the two are
    checked against each other. A disagreement means the contract value used
    here is not the one the venue applied, which is worth refusing over rather
    than picking a side.
    """
    context = "open-interest"
    contracts = _decimal(open_interest, "oi", context)
    converted = contracts * contract_value
    published = _decimal(open_interest, "oiCcy", context)
    if published != 0 and abs(converted - published) / published > Decimal("0.0001"):
        raise UnknownContractValue(
            f"{context}: oi * ctVal is {converted} but the venue publishes {published}; "
            "the contract value in hand is not the one it applied"
        )
    return published


def derivatives_state(
    *,
    funding: dict[str, Any],
    open_interest: dict[str, Any],
    mark: dict[str, Any],
    index: dict[str, Any],
    contract_value: Decimal,
    venue: str,
    market_type: str,
    ingest_time_ns: int,
    max_spread_ns: int,
) -> AssembledDerivatives:
    """Four public responses into the state the other venues produce in one.

    **`fundingTime` is the settlement this rate pays at**, and `nextFundingTime`
    is the one after. Bybit calls the first of those `nextFundingTime`, so the
    like-named fields on the two venues are eight hours apart -- measured, on
    2026-09-12, where OKX's `fundingTime` and Bybit's `nextFundingTime` were the
    same millisecond. Mapping by name puts one venue a settlement period out,
    and a dispersion computed across that boundary compares a settled rate
    against a forthcoming one.

    **The venue's `premium` is not this basis.** It looks like one and is
    averaged over a funding window; measured, the two are 0.14 basis points
    apart. Using it would compare OKX's window against Bybit's instant under one
    name, so the basis here is computed from mark and index exactly as Bybit's
    is.

    `max_spread_ns` has no default. How stale is too stale is a property of what
    the state is for -- a funding dispersion tolerates more than a basis -- and
    a default would be this module quietly deciding that for every caller.
    """
    context = "derivatives"
    if max_spread_ns <= 0:
        raise ValueError("a state assembled from four readings needs a bound on their spread")

    inst_id = str(_require(funding, "instId", context))
    for other, name in ((open_interest, "open-interest"), (mark, "mark-price")):
        if other.get("instId") != inst_id:
            raise NormalizationError(
                f"{context}: {name} is for {other.get('instId')!r}, not {inst_id!r}"
            )

    stamps = [
        int(_require(open_interest, "ts", context)),
        int(_require(mark, "ts", context)),
        int(_require(index, "ts", context)),
    ]
    oldest_ms, newest_ms = min(stamps), max(stamps)
    spread_ns = (newest_ms - oldest_ms) * MS_TO_NS
    if spread_ns > max_spread_ns:
        raise StaleAssembly(
            f"{context}: readings span {spread_ns}ns, more than the {max_spread_ns}ns allowed"
        )

    mark_price = _decimal(mark, "markPx", context)
    index_price = _decimal(index, "idxPx", context)
    rate = funding.get("fundingRate")
    settlement = funding.get("fundingTime")

    state = DerivativesState(
        meta=EventMeta(
            source=f"{venue}-rest",
            venue=venue,
            market_type=market_type,
            symbol=inst_id,
            # The oldest of the four. A state is no fresher than its stalest
            # part, and stamping it with the newest would claim a freshness
            # none of it has.
            event_time_ns=oldest_ms * MS_TO_NS,
            ingest_time_ns=ingest_time_ns,
            sequence=None,
            source_event_id=None,
        ),
        mark_price=mark_price,
        index_price=index_price,
        funding_rate=None if rate in (None, "") else float(rate),
        next_funding_time_ns=None if settlement in (None, "") else int(settlement) * MS_TO_NS,
        open_interest_base=float(open_interest_base(open_interest, contract_value=contract_value)),
        open_interest_usd=(
            None if open_interest.get("oiUsd") in (None, "") else float(open_interest["oiUsd"])
        ),
        basis_bps=(None if index_price == 0 else float((mark_price / index_price - 1) * 10_000)),
    )
    return AssembledDerivatives(
        state=state, oldest_ns=oldest_ms * MS_TO_NS, newest_ns=newest_ms * MS_TO_NS
    )
