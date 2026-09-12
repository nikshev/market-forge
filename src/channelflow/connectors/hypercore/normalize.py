"""HyperCore message to canonical event, and a symbol table that refuses to guess.

# @trace: REQ-WP-048

Pure: takes a decoded message, returns a domain model, touches no socket -- the
shape [[REQ-WP-003]] established. PRD section 18.11.1 puts HyperCore's output
into the same CLOB primitives Binance, Bybit and OKX produce, so it joins the
order-flow and derivatives paths rather than the AMM one.

**Symbol normalization is the substance here, not a detail.** Section 18.25 lists
it as one line; on this venue it is where the failures live. Measured against
the live API:

* **`allMids` keys arrive in three shapes** -- 235 bare, 380 beginning `@`, 382
  beginning `#`. A key is not a symbol until something says which shape it is.
* **Delisted perps keep their index.** 56 of 234 are delisted, the first at index
  3, and `metaAndAssetCtxs` is positional against the same list. A table built by
  enumerating what is still listed is right for BTC, ETH and ATOM and wrong for
  everything after, by a drift that grows with the index.
* **Spot pairs are sparse the other way.** 326 pairs with indices to 716, so the
  pair at position `i` is not pair `i`. One venue, two index conventions, and the
  two mistakes are opposites -- which is why this module has two lookups and not
  one clever one.
* **The two endpoints are not a snapshot of each other.** 55 `@N` keys in
  `allMids` matched no pair in a `spotMeta` read seconds earlier. Such a key is
  refused, because the alternative is resolving it to a neighbour.
* **`#N` is not established.** Its values arrive in pairs summing to one, which
  is consistent with binary markets and is not evidence. Refused until someone
  can say what it is.

**What `side` means was measured, not assumed.** A trade carries `"B"` or `"A"`,
which could be the taker's direction or the resting side it hit. Interleaved with
the best bid and offer over 143 recorded trades: `"B"` executed at or above the
ask 47 times out of 47, and `"A"` at or below the bid 35 times out of 36. That is
the taker's side. The single exception arrived before the quote update that had
already moved the price, which is what an interleaved recording looks like.

A test over the committed fixtures asserts this, because a test fails when the
venue changes and a sentence in a docstring does not.

**`l2Book.levels` is positional**: `[[bids], [asks]]` with nothing labelling
which. Read in the wrong order the book is *crossed* rather than empty -- and a
crossed book is a signal, which makes that error worse than a missing one.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal

from channelflow.domain import (
    BookSnapshot,
    DerivativesState,
    EventMeta,
    PriceLevel,
    TradeEvent,
)

SOURCE = "hyperliquid-ws"
VENUE = "hyperliquid"
MS_TO_NS = 1_000_000

#: Measured from 143 interleaved recorded trades; see the module docstring.
_TAKER: dict[str, Literal["buy", "sell"]] = {"B": "buy", "A": "sell"}

#: `l2Book.levels` and `bbo` both arrive as two positional sides.
_BID_SIDE = 0
_ASK_SIDE = 1


class NormalizationError(ValueError):
    """A message did not carry what this venue's own shape requires."""


class UnknownSymbol(NormalizationError):
    """A key could not be resolved to an instrument.

    Refused rather than passed through. A key that names nothing, carried into a
    feature, becomes a series attributed to an instrument that does not exist --
    and on this venue the keys that name nothing look exactly like the ones that
    do.
    """


class CrossedBook(NormalizationError):
    """The best bid is at or above the best ask.

    Which is what reading `levels` in the wrong order produces. An empty book is
    obviously broken; a crossed one is a tradeable signal, so it has to be
    refused rather than published.
    """


class Namespace(StrEnum):
    """Which of the venue's naming schemes a key belongs to."""

    PERP = "perp"
    SPOT = "spot"
    BUILDER_PERP = "builder_perp"


def _require(raw: dict[str, Any], key: str, context: str) -> Any:
    if key not in raw:
        raise NormalizationError(f"{context}: missing {key!r}")
    return raw[key]


def _decimal(raw: dict[str, Any], key: str, context: str) -> Decimal:
    try:
        return Decimal(str(_require(raw, key, context)))
    except InvalidOperation as exc:
        raise NormalizationError(f"{context}: {key!r} is not a number: {raw[key]!r}") from exc


def _levels(rows: Any, context: str) -> tuple[PriceLevel, ...]:
    if not isinstance(rows, list):
        raise NormalizationError(f"{context}: levels must be a list, got {type(rows).__name__}")
    return tuple(
        PriceLevel(price=_decimal(row, "px", context), qty=_decimal(row, "sz", context))
        for row in rows
    )


class SymbolTable:
    """The venue's own naming, as of one metadata read.

    Built from `meta`, `spotMeta` and `perpDexs` together, because no one of them
    covers the key space. Holding them as one object is also what makes the
    staleness visible: a table is a snapshot, and a key minted after it was taken
    is refused rather than silently resolved against an older world.
    """

    def __init__(
        self,
        *,
        meta: dict[str, Any],
        spot_meta: dict[str, Any],
        perp_dexes: list[Any] | None = None,
    ) -> None:
        universe = _require(meta, "universe", "meta")
        # Positional, delisted included. Compacting this is the error the module
        # docstring is about.
        self._perps: tuple[str, ...] = tuple(str(asset["name"]) for asset in universe)
        self._delisted: frozenset[int] = frozenset(
            index for index, asset in enumerate(universe) if asset.get("isDelisted")
        )
        # By the pair's own `index`, never by its position.
        self._spot: dict[int, str] = {
            int(pair["index"]): str(pair["name"])
            for pair in _require(spot_meta, "universe", "spotMeta")
        }
        self._tokens: dict[int, dict[str, Any]] = {
            int(token["index"]): token for token in _require(spot_meta, "tokens", "spotMeta")
        }
        self._pair_tokens: dict[int, tuple[int, int]] = {
            int(pair["index"]): (int(pair["tokens"][0]), int(pair["tokens"][1]))
            for pair in spot_meta["universe"]
        }
        self._dexes: frozenset[str] = frozenset(
            str(entry["name"]) for entry in (perp_dexes or []) if entry
        )

    @property
    def perp_count(self) -> int:
        return len(self._perps)

    @property
    def delisted_indices(self) -> frozenset[int]:
        return self._delisted

    def perp_at(self, index: int) -> str:
        """The perp at a venue index, counting delisted assets.

        `metaAndAssetCtxs` is positional against the same list, so an index that
        skipped delisted assets would pair a context with another asset's name --
        two live markets' numbers under one symbol.
        """
        if not 0 <= index < len(self._perps):
            raise UnknownSymbol(f"perp index {index} outside the venue's {len(self._perps)}")
        return self._perps[index]

    def spot_at(self, index: int) -> str:
        """The spot pair with this `index`, which is not its position."""
        if index not in self._spot:
            raise UnknownSymbol(f"spot pair {index} is not in this metadata read")
        return self._spot[index]

    def pair_tokens(self, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """The base and quote token records of a spot pair, in that order."""
        if index not in self._pair_tokens:
            raise UnknownSymbol(f"spot pair {index} is not in this metadata read")
        base, quote = self._pair_tokens[index]
        return self._tokens[base], self._tokens[quote]

    def resolve(self, key: str) -> tuple[Namespace, str]:
        """Which scheme a key belongs to and what it names.

        Every branch either names something the metadata contains or refuses.
        There is deliberately no fallback: on this venue an unresolvable key is
        shaped exactly like a resolvable one.
        """
        if not key:
            raise UnknownSymbol("an empty key names nothing")
        if key.startswith("#"):
            raise UnknownSymbol(
                f"{key!r}: the '#' namespace is not established. Its values arrive in "
                "pairs summing to one, which is consistent with binary markets and is "
                "not evidence"
            )
        if key.startswith("@"):
            digits = key[1:]
            if not digits.isdigit():
                raise UnknownSymbol(f"{key!r}: '@' must be followed by a pair index")
            return Namespace.SPOT, self.spot_at(int(digits))
        if ":" in key:
            dex, _, asset = key.partition(":")
            if dex not in self._dexes:
                raise UnknownSymbol(f"{key!r}: no deployed perp dex named {dex!r}")
            if not asset:
                raise UnknownSymbol(f"{key!r}: no asset after the dex")
            return Namespace.BUILDER_PERP, key
        if key not in self._perps:
            raise UnknownSymbol(f"{key!r} is not a perp in this metadata read")
        return Namespace.PERP, key


def evm_wei(token: dict[str, Any], size: Decimal) -> int:
    """A HyperCore size as the amount its HyperEVM contract would hold.

    Two adjustments, and the second is the one that bites. `weiDecimals` scales
    the size; `evmContract.evm_extra_wei_decimals` then shifts it again, and it
    is `-2` for USDC. Section 18.11.3's cross-layer features compare a HyperCore
    mid against a HyperEVM DEX price, so a factor of a hundred in between would
    read as an arbitrage rather than as a units mistake.
    """
    contract = token.get("evmContract")
    if contract is None:
        raise UnknownSymbol(f"{token.get('name')!r} has no HyperEVM contract")
    decimals = int(_require(token, "weiDecimals", "token")) + int(
        _require(contract, "evm_extra_wei_decimals", "evmContract")
    )
    if decimals < 0:
        raise NormalizationError(f"{token.get('name')!r} resolves to {decimals} decimals")
    return int(size * Decimal(10) ** decimals)


def order_book(message: dict[str, Any], *, market_type: str, ingest_time_ns: int) -> BookSnapshot:
    """An `l2Book` payload. Always a snapshot: the venue sends no deltas here."""
    context = "l2Book"
    levels = _require(message, "levels", context)
    if not isinstance(levels, list) or len(levels) != 2:
        raise NormalizationError(f"{context}: levels must be exactly two sides")

    bids = _levels(levels[_BID_SIDE], context)
    asks = _levels(levels[_ASK_SIDE], context)
    if bids and asks and bids[0].price >= asks[0].price:
        raise CrossedBook(f"{context}: best bid {bids[0].price} >= best ask {asks[0].price}")

    event_time_ns = int(_require(message, "time", context)) * MS_TO_NS
    return BookSnapshot(
        meta=EventMeta(
            source=SOURCE,
            venue=VENUE,
            market_type=market_type,
            symbol=str(_require(message, "coin", context)),
            event_time_ns=event_time_ns,
            ingest_time_ns=ingest_time_ns,
            # The venue gives no update id, and its timestamp is what orders one
            # book against the next. Using it as the id says that plainly rather
            # than inventing a counter that would look like the venue's.
            sequence=event_time_ns,
            source_event_id=None,
        ),
        update_id=event_time_ns,
        bids=bids,
        asks=asks,
    )


def best_bid_offer(
    message: dict[str, Any], *, market_type: str, ingest_time_ns: int
) -> BookSnapshot:
    """A `bbo` payload, which is a two-level book and normalizes as one.

    Either side may be null when nothing rests there. That is an absent quote,
    not a quote of zero -- so the side comes back empty and the caller can tell.
    """
    context = "bbo"
    sides = _require(message, "bbo", context)
    if not isinstance(sides, list) or len(sides) != 2:
        raise NormalizationError(f"{context}: bbo must be exactly two sides")
    return order_book(
        {
            "coin": _require(message, "coin", context),
            "time": _require(message, "time", context),
            "levels": [
                [] if sides[_BID_SIDE] is None else [sides[_BID_SIDE]],
                [] if sides[_ASK_SIDE] is None else [sides[_ASK_SIDE]],
            ],
        },
        market_type=market_type,
        ingest_time_ns=ingest_time_ns,
    )


def public_trade(raw: dict[str, Any], *, market_type: str, ingest_time_ns: int) -> TradeEvent:
    """One fill from the `trades` channel.

    Size is already in base units on this venue -- there is no contract
    multiplier to apply, unlike OKX ([[REQ-WP-044]]). Stating that is worth a
    line: the absence of a conversion is a fact about the venue, and a reader who
    assumes it by analogy with the neighbour connector would be right here and
    wrong there.
    """
    context = "trades"
    side = str(_require(raw, "side", context))
    if side not in _TAKER:
        raise NormalizationError(f"{context}: unknown taker side {side!r}")

    price = _decimal(raw, "px", context)
    qty_base = _decimal(raw, "sz", context)
    trade_id = str(_require(raw, "tid", context))

    return TradeEvent(
        meta=EventMeta(
            source=SOURCE,
            venue=VENUE,
            market_type=market_type,
            symbol=str(_require(raw, "coin", context)),
            event_time_ns=int(_require(raw, "time", context)) * MS_TO_NS,
            ingest_time_ns=ingest_time_ns,
            sequence=int(trade_id),
            source_event_id=trade_id,
        ),
        trade_id=trade_id,
        price=price,
        qty_base=qty_base,
        notional_quote=price * qty_base,
        aggressor_side=_TAKER[side],
        # The venue names the taker, so the buyer was the maker exactly when the
        # taker was the seller.
        is_buyer_maker=side == "A",
    )


def asset_context(
    raw: dict[str, Any], *, symbol: str, market_type: str, event_time_ns: int, ingest_time_ns: int
) -> DerivativesState:
    """One entry of `metaAndAssetCtxs`'s second element.

    Every field is optional, and an absent one stays `None`. A funding rate of
    zero is a market in balance; a funding rate nobody published is a market
    nobody measured, and flattening the second into the first is the error
    [[REQ-WP-031]] is named after.
    """
    context = "assetCtx"

    def maybe(key: str) -> Decimal | None:
        return None if raw.get(key) is None else _decimal(raw, key, context)

    mark = maybe("markPx")
    oracle = maybe("oraclePx")
    basis_bps = None
    if mark is not None and oracle is not None and oracle != 0:
        basis_bps = float((mark / oracle - 1) * 10_000)

    funding = raw.get("funding")
    open_interest = raw.get("openInterest")
    return DerivativesState(
        meta=EventMeta(
            source=SOURCE,
            venue=VENUE,
            market_type=market_type,
            symbol=symbol,
            event_time_ns=event_time_ns,
            ingest_time_ns=ingest_time_ns,
            sequence=None,
            source_event_id=None,
        ),
        mark_price=mark,
        # The venue's oracle price is its index: an external reference, not a
        # figure derived from its own book.
        index_price=oracle,
        funding_rate=None if funding is None else float(funding),
        open_interest_base=None if open_interest is None else float(open_interest),
        basis_bps=basis_bps,
    )
