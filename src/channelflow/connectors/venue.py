"""Venue abstraction for multi-venue ingest.

# @trace: REQ-WP-076
# @trace: REQ-WP-078

The ingest daemon currently knows only Binance. This module introduces a
`VenueConnector` protocol that abstracts the connection lifecycle per venue,
so the session and daemon stay venue-agnostic.

Each venue has its own:
- Stream builder (what streams to request)
- Subscription mechanism (Binance: URL params; Bybit/OKX: post-connect message)
- VenuePolicy (keepalive, idle timeout, reconnect rules)
- Archive prefix (for raw frame storage)
"""

from __future__ import annotations

import json
import queue
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from channelflow.connectors.session import BINANCE, BYBIT, OKX, VenuePolicy


class VenueConnector(Protocol):
    """Full connection lifecycle for one venue."""

    def connect(self, streams: Sequence[str]) -> None:
        """Open socket, send subscription if needed, start reader thread."""

    def send(self, payload: str) -> None:
        """Send a text frame to the venue."""

    def pong(self) -> None:
        """Respond to a venue ping (if venue expects client pong)."""

    def close(self) -> None:
        """Close the connection cleanly."""

    def drain_frames(self) -> list[str]:
        """Return all frames that have arrived since the last call, without waiting.

        This is the seam that allows both live and replay transports to be used
        interchangeably: the live transport drains its internal queue, the replay
        transport returns its pending recorded frames.
        """

    @property
    def alive(self) -> bool:
        """True from `connect` until the reader returns for **any** reason.

        A fact about the reader and not about the venue. The reader logs why it ended
        where the exception is in hand; the session polls this to know that it did.
        """

    @property
    def frames(self) -> queue.Queue[str]:
        """Incoming frames queue (for backward compatibility with code that
        inspects the queue directly)."""


@dataclass(frozen=True)
class VenueConfig:
    """Configuration for one venue's live ingest."""

    # The dotted path of the connector class, not the class itself: importing
    # every venue's connector here would couple this registry to each venue's
    # heaviest dependency (in the limit, an SDK). The daemon resolves the path
    # where it builds the connector (`ingest_main._resolve_connector`).
    connector: str
    #: Stream **labels**, for the session and the log: `trades.BTC-USDT-SWAP`.
    stream_builder: Callable[[Sequence[str]], tuple[str, ...]]
    policy: VenuePolicy
    #: The WebSocket endpoint, or `None` where the URL is built from the streams (Binance
    #: subscribes by URL, so its connector is handed a function and not an address).
    url: str | None
    #: The message sent after connecting, built from **symbols** -- `BTC-USDT-SWAP` -- and
    #: not from stream labels. OKX's label is `trades.BTC-USDT-SWAP` and its `instId` is
    #: `BTC-USDT-SWAP`; feeding the first to the second is what OKX rejected with
    #: "Subscribe failed". `None` where nothing is sent.
    subscribe_message: Callable[[Sequence[str]], str | None]


def binance_streams(symbols: Sequence[str]) -> tuple[str, ...]:
    """Binance stream names: lowercase symbol + @aggTrade."""
    return tuple(f"{s.lower()}@aggTrade" for s in symbols)


def bybit_streams(symbols: Sequence[str]) -> tuple[str, ...]:
    """Bybit V5 public trade stream names."""
    return tuple(f"publicTrade.{s}" for s in symbols)


def okx_streams(symbols: Sequence[str]) -> tuple[str, ...]:
    """OKX v5 trades channel stream names."""
    return tuple(f"trades.{s}" for s in symbols)


def binance_subscribe_message(streams: Sequence[str]) -> str | None:
    """Binance uses URL params for subscription; no post-connect message."""
    return None


def bybit_subscribe_message(streams: Sequence[str]) -> str:
    """Bybit V5 subscribe message after connect."""
    return '{"op":"subscribe","args":' + str(list(streams)).replace("'", '"') + "}"


def okx_subscribe_message(instruments: Sequence[str]) -> str:
    """OKX v5 subscribe message after connect, from **instruments** (`BTC-USDT-SWAP`).

    Not from stream labels: `instId` is the instrument as OKX names it, and a label such as
    `trades.BTC-USDT-SWAP` is answered with "Subscribe failed ... doesn't exist".
    """
    args = [{"channel": "trades", "instId": s} for s in instruments]
    return '{"op":"subscribe","args":' + json.dumps(args) + "}"


def binance_subscription(symbols: Sequence[str]) -> str | None:
    """Binance subscribes through its URL; nothing is sent."""
    return None


def bybit_subscription(symbols: Sequence[str]) -> str:
    return bybit_subscribe_message(bybit_streams(symbols))


def okx_subscription(symbols: Sequence[str]) -> str:
    return okx_subscribe_message(symbols)


def rejection(venue: str, frame: str) -> str | None:
    """The venue's own words when `frame` is its refusal of a request, else `None`.

    Pure and total: a frame that is not JSON, or has any other shape, is `None`. Pinned
    against frames captured live on 2026-10-02.

    * OKX answers `{"event":"error","msg":"Subscribe failed, ..."}`.
    * Bybit answers `{"success":false,"ret_msg":"error:handler not found,topic:..."}`.
    * Binance has no rule: its combined-stream endpoint answered a malformed stream name
      by connecting and delivering nothing, so there is no refusal frame to read, and a
      rule written from a description of a format nobody saw would be an invented frame.
    """
    try:
        data = json.loads(frame)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if venue == "okx" and data.get("event") == "error":
        message = data.get("msg")
        return message if isinstance(message, str) else "error (no message)"
    if venue == "bybit" and data.get("success") is False:
        message = data.get("ret_msg")
        return message if isinstance(message, str) else "request failed (no message)"
    return None


# Venue registry: the single source of truth for venue wiring
VENUE_REGISTRY = {
    "binance": VenueConfig(
        connector="channelflow.connectors.binance.connector.BinanceConnector",
        stream_builder=binance_streams,
        policy=BINANCE,
        url=None,
        subscribe_message=binance_subscription,
    ),
    "bybit": VenueConfig(
        connector="channelflow.connectors.bybit.connector.BybitConnector",
        stream_builder=bybit_streams,
        policy=BYBIT,
        url="wss://stream.bybit.com/v5/public/linear",
        subscribe_message=bybit_subscription,
    ),
    "okx": VenueConfig(
        connector="channelflow.connectors.okx.connector.OkxConnector",
        stream_builder=okx_streams,
        policy=OKX,
        # OKX's v5 public WebSocket. `wss://ws.okx.com/api/v5/market`, which this once
        # was, is a REST path prefix: connecting to it answers `HTTP 404`.
        url="wss://ws.okx.com:8443/ws/v5/public",
        subscribe_message=okx_subscription,
    ),
}
