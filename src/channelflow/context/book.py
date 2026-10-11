"""The order-book streams of each venue as a collector task (REQ-WP-095).

# @trace: REQ-WP-095

What to connect to, how to read what arrives, and what to keep. The raw book is not stored: each
frame goes to a `MinuteBook` (one per symbol), which finalises a summary per minute in event time,
and those go to the sink with the quote they imply.

**One book per market the series is.** Binance's series are *spot* markets (the trade ingest
connects to `stream.binance.com`), so their book is the spot partial-depth stream; Bybit's and
OKX's series are the perpetuals, so theirs are the perpetuals' books. A book is never attributed
to a market it is not.

**Streams, and why these** (all probed from this host on 2026-10-11):

* Binance spot `<symbol>@depth10@1000ms`: a whole top-ten snapshot a second, so there is no delta
  chain to keep. It carries no timestamp, so receipt time stands in for event time -- stated in
  `connectors.binance.normalize.depth_snapshot`, where it already was.
* Bybit linear `orderbook.50.<symbol>`: a snapshot, then deltas with a continuous `u`; the existing
  `BookService` detects a gap and the collector reconnects to get a fresh snapshot.
* OKX `books`: a 400-level snapshot, then updates with a `prevSeqId`/`seqId` chain, handled the
  same way. (`books5` would be snapshot-only but has five levels, and ten are asked for.) **Sizes
  are contracts**: converted to base units with the instrument's own contract value, so the
  order-flow imbalance is in the same unit on every venue.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.connectors.binance import normalize as binance_normalize
from channelflow.connectors.binance.connector import BinanceConnector
from channelflow.connectors.bybit import normalize as bybit_normalize
from channelflow.connectors.bybit.connector import BybitConnector
from channelflow.connectors.okx import normalize as okx_normalize
from channelflow.connectors.okx.connector import OkxConnector
from channelflow.connectors.session import Clock, StreamSession
from channelflow.connectors.websocket import binance_stream_url
from channelflow.context.minute_book import MinuteBook, MinuteSummary
from channelflow.context.streams import StreamTask, stream_policy
from channelflow.domain import BookDelta, BookSnapshot, PriceLevel
from channelflow.tables.book_minutes import BookMinuteSink

BOOK_VENUES = ("binance", "bybit", "okx")

BYBIT_URL = "wss://stream.bybit.com/v5/public/linear"
OKX_URL = "wss://ws.okx.com:8443/ws/v5/public"

#: The market each venue's book is of (see the module docstring).
MARKET_TYPE = {"binance": "spot", "bybit": "perp", "okx": "perp"}


@dataclass(frozen=True)
class BookStreamSpec:
    venue: str
    url: str
    subscribe_message: str | None
    streams: tuple[str, ...]


def stream_spec(venue: str, symbols: Sequence[str]) -> BookStreamSpec:
    if venue == "binance":
        streams = tuple(f"{symbol.lower()}@depth10@1000ms" for symbol in symbols)
        return BookStreamSpec(venue, binance_stream_url(streams), None, streams)
    if venue == "bybit":
        topics = tuple(f"orderbook.50.{symbol}" for symbol in symbols)
        message = json.dumps({"op": "subscribe", "args": list(topics)})
        return BookStreamSpec(venue, BYBIT_URL, message, topics)
    if venue == "okx":
        args = [{"channel": "books", "instId": symbol} for symbol in symbols]
        message = json.dumps({"op": "subscribe", "args": args})
        return BookStreamSpec(venue, OKX_URL, message, tuple(f"books.{s}" for s in symbols))
    raise ValueError(f"no book stream for venue {venue!r}; known: {', '.join(BOOK_VENUES)}")


def _scaled(message: BookSnapshot | BookDelta, factor: Decimal) -> BookSnapshot | BookDelta:
    def scale(levels: tuple[PriceLevel, ...]) -> tuple[PriceLevel, ...]:
        return tuple(PriceLevel(price=level.price, qty=level.qty * factor) for level in levels)

    return message.model_copy(update={"bids": scale(message.bids), "asks": scale(message.asks)})


def message_of(
    venue: str,
    frame: dict[str, object],
    ingest_time_ns: int,
    contract_values: Mapping[str, Decimal | None],
) -> tuple[str, BookSnapshot | BookDelta] | None:
    """`(symbol, message)` for a book frame, or `None` for anything else (acks, pongs)."""
    if venue == "binance":
        stream, data = frame.get("stream"), frame.get("data")
        if not isinstance(stream, str) or "@depth" not in stream or not isinstance(data, dict):
            return None
        symbol = stream.split("@", 1)[0].upper()
        snapshot = binance_normalize.depth_snapshot(
            data,
            venue="binance",
            market_type="spot",
            symbol=symbol,
            ingest_time_ns=ingest_time_ns,
        )
        meta = snapshot.meta.model_copy(update={"source": "binance-ws-depth"})
        return symbol, snapshot.model_copy(update={"meta": meta})
    if venue == "bybit":
        topic = frame.get("topic")
        if not isinstance(topic, str) or not topic.startswith("orderbook."):
            return None
        message = bybit_normalize.order_book_message(
            frame, venue="bybit", market_type="perp", ingest_time_ns=ingest_time_ns
        )
        return message.meta.symbol, message
    if venue == "okx":
        arg = frame.get("arg")
        if not isinstance(arg, dict) or arg.get("channel") != "books" or "data" not in frame:
            return None
        message = okx_normalize.order_book_message(
            frame, venue="okx", market_type="perp", ingest_time_ns=ingest_time_ns
        )
        contract_value = contract_values.get(message.meta.symbol)
        if contract_value is None or contract_value <= 0:
            raise ValueError(
                f"{message.meta.symbol}: no usable contract value; book sizes in base units "
                "cannot be derived from contracts"
            )
        return message.meta.symbol, _scaled(message, contract_value)
    raise ValueError(f"no book parser for venue {venue!r}")


@dataclass
class BookHandler:
    """Frames in, finalised minutes out, to the sink; one `MinuteBook` per watched symbol."""

    venue: str
    symbols: Sequence[str]
    sink: BookMinuteSink
    contract_values: Mapping[str, Decimal | None]
    #: Called when a book has lost its sequence: the way to a fresh snapshot is a new connection.
    request_resync: Callable[[], None]
    books: dict[str, MinuteBook] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for symbol in self.symbols:
            self.books[symbol] = MinuteBook(venue=self.venue, symbol=symbol)

    def __call__(self, frame: str, received_at_ns: int) -> None:
        decoded = json.loads(frame)
        if not isinstance(decoded, dict):
            return
        item = message_of(self.venue, decoded, received_at_ns, self.contract_values)
        if item is None:
            return
        symbol, message = item
        book = self.books.get(symbol)
        if book is None:
            return
        for summary in book.feed(message):
            self._store(summary, received_at_ns)
        if book.needs_resync:
            self.request_resync()

    def tick(self, now_ns: int) -> None:
        for book in self.books.values():
            for summary in book.tick(now_ns=now_ns):
                self._store(summary, now_ns)

    def on_reconnect(self) -> None:
        for book in self.books.values():
            book.reset()

    def _store(self, summary: MinuteSummary, ingest_time_ns: int) -> None:
        self.sink(summary, ingest_time_ns=ingest_time_ns, market_type=MARKET_TYPE[self.venue])


def book_task(
    *,
    venue: str,
    symbols: Sequence[str],
    sink: BookMinuteSink,
    now_ns: Callable[[], int],
    on_failure: Callable[[str], None],
    contract_values: Mapping[str, Decimal | None] | None = None,
    clock: Clock | None = None,
    connector: object | None = None,
) -> StreamTask:
    """The task for one venue's books. `connector` and `clock` are injectable for a test."""
    spec = stream_spec(venue, symbols)
    if connector is None:
        if venue == "binance":
            connector = BinanceConnector(url_for=binance_stream_url)
        elif venue == "bybit":
            connector = BybitConnector(url=spec.url, subscribe_msg=spec.subscribe_message or "")
        else:
            connector = OkxConnector(url=spec.url, subscribe_msg=spec.subscribe_message or "")
    session = StreamSession(
        streams=spec.streams,
        policy=stream_policy(venue, quiet=False),
        connector=connector,
        clock=clock or _SystemClock(),
    )
    handler = BookHandler(
        venue=venue,
        symbols=symbols,
        sink=sink,
        contract_values=contract_values or {},
        request_resync=lambda: connector.close(),  # type: ignore[attr-defined]
    )
    return StreamTask(
        session=session,
        handler=handler,
        heartbeat=lambda boundary_ns: None,
        now_ns=now_ns,
        on_failure=on_failure,
        tick=handler.tick,
        on_reconnect=handler.on_reconnect,
    )


class _SystemClock:
    def now_ns(self) -> int:
        import time

        return time.time_ns()
