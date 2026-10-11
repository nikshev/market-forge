"""The liquidation stream of each venue as a collector task (REQ-WP-094).

# @trace: REQ-WP-094

What to connect to, how to read what arrives, and what to store: three small things per venue, and
nothing about connections, which is `streams.py`'s and the session's.

**Where each stream lives was measured on 2026-10-11, not copied from documentation.** Binance's
futures websocket moved to new paths: the legacy `/ws/` path no longer delivers `forceOrder` (it
connects and is silent, indistinguishable from a quiet market), and `/market/ws/` does. The
all-market stream (`!forceOrder@arr`) is used, filtered to the symbols asked for, because one
connection that carries every symbol is steadier evidence of being alive than a symbol's own
stream that can be silent for an hour."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from channelflow.connectors.binance import liquidation as binance_liquidation
from channelflow.connectors.binance.connector import BinanceConnector
from channelflow.connectors.bybit import liquidation as bybit_liquidation
from channelflow.connectors.bybit.connector import BybitConnector
from channelflow.connectors.okx import liquidation as okx_liquidation
from channelflow.connectors.okx.connector import OkxConnector
from channelflow.connectors.session import Clock, StreamSession
from channelflow.context.streams import StreamTask, stream_policy
from channelflow.domain import LiquidationEvent
from channelflow.tables.liquidations import Heartbeat, LiquidationSink

LIQUIDATION_VENUES = ("binance", "bybit", "okx")

BINANCE_URL = "wss://fstream.binance.com/market/ws/"
BYBIT_URL = "wss://stream.bybit.com/v5/public/linear"
OKX_URL = "wss://ws.okx.com:8443/ws/v5/public"


@dataclass(frozen=True)
class LiquidationStreamSpec:
    """Where to connect and what to ask for; pure, so a test can read it."""

    venue: str
    url: str
    #: The subscription message sent after connecting, or `None` where the URL is the subscription.
    subscribe_message: str | None
    streams: tuple[str, ...]


def stream_spec(venue: str, symbols: Sequence[str]) -> LiquidationStreamSpec:
    if venue == "binance":
        return LiquidationStreamSpec(
            venue=venue,
            url=BINANCE_URL + "!forceOrder@arr",
            subscribe_message=None,
            streams=("!forceOrder@arr",),
        )
    if venue == "bybit":
        topics = tuple(f"allLiquidation.{symbol}" for symbol in symbols)
        return LiquidationStreamSpec(
            venue=venue,
            url=BYBIT_URL,
            subscribe_message=json.dumps({"op": "subscribe", "args": list(topics)}),
            streams=topics,
        )
    if venue == "okx":
        argument = {"channel": "liquidation-orders", "instType": "SWAP"}
        return LiquidationStreamSpec(
            venue=venue,
            url=OKX_URL,
            subscribe_message=json.dumps({"op": "subscribe", "args": [argument]}),
            streams=("liquidation-orders",),
        )
    raise ValueError(
        f"no liquidation stream for venue {venue!r}; known: {', '.join(LIQUIDATION_VENUES)}"
    )


def parser_for(
    venue: str,
    symbols: Sequence[str],
    contract_values: Mapping[str, Decimal | None],
) -> Callable[[dict[str, object], int], list[LiquidationEvent]]:
    """`(decoded frame, ingest time) -> events` for one venue, filtered to the symbols watched."""
    watched = frozenset(symbols)
    if venue == "binance":
        return lambda frame, at: binance_liquidation.liquidation_events(
            frame, ingest_time_ns=at, symbols=watched
        )
    if venue == "bybit":
        return lambda frame, at: bybit_liquidation.liquidation_events(
            frame, ingest_time_ns=at, symbols=watched
        )
    if venue == "okx":
        values = {symbol: contract_values.get(symbol) for symbol in symbols}
        return lambda frame, at: okx_liquidation.liquidation_events(
            frame, ingest_time_ns=at, contract_values=values
        )
    raise ValueError(f"no liquidation parser for venue {venue!r}")


def frame_handler(
    parse: Callable[[dict[str, object], int], list[LiquidationEvent]], sink: LiquidationSink
) -> Callable[[str, int], None]:
    """Decode a frame, parse it, store what it holds. Not JSON raises, and is counted."""

    def handle(frame: str, received_at_ns: int) -> None:
        if frame.strip() == "pong":
            return  # OKX answers a ping with the bare word: not JSON, and not a fault
        decoded = json.loads(frame)
        if not isinstance(decoded, dict):
            return  # a JSON string or number: not a liquidation, not an error
        for event in parse(decoded, received_at_ns):
            sink(event)

    return handle


def heartbeat_writer(
    venue: str, symbols: Sequence[str], sink: LiquidationSink
) -> Callable[[int], None]:
    def write(boundary_ns: int) -> None:
        for symbol in symbols:
            sink.heartbeat(Heartbeat(venue=venue, symbol=symbol, at_ns=boundary_ns))

    return write


def liquidation_task(
    *,
    venue: str,
    symbols: Sequence[str],
    sink: LiquidationSink,
    now_ns: Callable[[], int],
    on_failure: Callable[[str], None],
    contract_values: Mapping[str, Decimal | None] | None = None,
    clock: Clock | None = None,
    connector: object | None = None,
) -> StreamTask:
    """The task for one venue. `connector` and `clock` are injectable for a test."""
    spec = stream_spec(venue, symbols)
    if connector is None:
        if venue == "binance":
            connector = BinanceConnector(url_for=lambda streams: BINANCE_URL + streams[0])
        elif venue == "bybit":
            connector = BybitConnector(url=spec.url, subscribe_msg=spec.subscribe_message or "")
        else:
            connector = OkxConnector(url=spec.url, subscribe_msg=spec.subscribe_message or "")
    session = StreamSession(
        streams=spec.streams,
        policy=stream_policy(venue, quiet=True),
        connector=connector,
        clock=clock or _SystemClock(),
    )
    return StreamTask(
        session=session,
        handler=frame_handler(parser_for(venue, symbols, contract_values or {}), sink),
        heartbeat=heartbeat_writer(venue, symbols, sink),
        now_ns=now_ns,
        on_failure=on_failure,
    )


class _SystemClock:
    def now_ns(self) -> int:
        import time

        return time.time_ns()
