"""Venue abstraction for multi-venue ingest.

# @trace: REQ-WP-076

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

import queue
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from channelflow.connectors.session import Keepalive, VenuePolicy


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

    @property
    def frames(self) -> queue.Queue[str]:
        """Incoming frames queue."""


@dataclass(frozen=True)
class VenueConfig:
    """Configuration for one venue's live ingest."""

    connector: type
    stream_builder: Callable[[Sequence[str]], tuple[str, ...]]
    policy: VenuePolicy
    archive_prefix: str


# Venue policies (measured 2026-09-12, recorded in session.py)
# Bybit: ~60s idle, no close frame, client sends {"op":"ping"}
# OKX: ~31s idle, code 4004, client sends bare "ping"
# Binance: 24 hours, protocol ping/pong

BINANCE_POLICY = VenuePolicy(
    venue="binance",
    keepalive=Keepalive.SERVER_INITIATED,
    idle_timeout_ns=24 * 60 * 60 * 1_000_000_000,  # 24 hours
    client_ping_interval_ns=None,
    ping_payload=None,
    announces_close=True,
    min_connect_interval_ns=1_000_000_000,
)

BYBIT_POLICY = VenuePolicy(
    venue="bybit",
    keepalive=Keepalive.CLIENT_INITIATED,
    idle_timeout_ns=60_700_000_000,  # ~60.7s (measured)
    client_ping_interval_ns=20_000_000_000,  # 20s (Bybit sends ping ~20s)
    ping_payload='{"op":"ping"}',
    announces_close=False,  # Bybit sends no close frame
    min_connect_interval_ns=1_000_000_000,
)

OKX_POLICY = VenuePolicy(
    venue="okx",
    keepalive=Keepalive.CLIENT_INITIATED,
    idle_timeout_ns=30_900_000_000,  # ~30.9s (measured)
    client_ping_interval_ns=20_000_000_000,  # 20s
    ping_payload="ping",  # bare string "ping"
    announces_close=True,  # closes with code 4004
    min_connect_interval_ns=1_000_000_000,
)


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


def okx_subscribe_message(streams: Sequence[str]) -> str:
    """OKX v5 subscribe message after connect."""
    import json

    args = [{"channel": "trades", "instId": s} for s in streams]
    return '{"op":"subscribe","args":' + json.dumps(args) + "}"


# Venue registry: the single source of truth for venue wiring
VENUE_REGISTRY = {
    "binance": VenueConfig(
        connector="channelflow.connectors.binance.connector.BinanceConnector",
        stream_builder=binance_streams,
        policy=BINANCE_POLICY,
        archive_prefix="binance",
    ),
    "bybit": VenueConfig(
        connector="channelflow.connectors.bybit.connector.BybitConnector",
        stream_builder=bybit_streams,
        policy=BYBIT_POLICY,
        archive_prefix="bybit",
    ),
    "okx": VenueConfig(
        connector="channelflow.connectors.okx.connector.OkxConnector",
        stream_builder=okx_streams,
        policy=OKX_POLICY,
        archive_prefix="okx",
    ),
}
