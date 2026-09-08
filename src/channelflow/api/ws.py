"""PRD section 28.7's live channel.

# @trace: REQ-API-001

    {"op": "subscribe", "venue": "binance", "symbol": "BTCUSDT",
     "timeframe": "15m", "channels": ["bars", "channel", "features", "signals"]}

A subscription is a filter, and the filter is the feature: a subscriber that
asked for bars and receives signals has been given data it did not ask to
handle, and a chart that renders it will show something its user did not
request.

A malformed message is answered, not fatal (FR-012). Closing the connection on
a bad frame turns a client bug into an outage, and the client cannot see the
reason it was disconnected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

#: The four PRD section 28.7 names. Anything else is a typo, and a typo that
#: silently subscribed to nothing would look exactly like a quiet market.
CHANNELS = frozenset({"bars", "channel", "features", "signals"})


@dataclass(frozen=True)
class Subscription:
    venue: str
    symbol: str
    timeframe: str
    channels: frozenset[str]

    def wants(self, *, channel: str, venue: str, symbol: str, timeframe: str) -> bool:
        return (
            channel in self.channels
            and venue == self.venue
            and symbol == self.symbol
            and timeframe == self.timeframe
        )


class SubscribeError(ValueError):
    """The message was not a subscription this can act on."""


def parse_subscribe(raw: str) -> Subscription:
    """PRD section 28.7's message, or a stated reason it is not one."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SubscribeError(f"not JSON: {exc}") from exc
    if not isinstance(message, dict):
        raise SubscribeError("expected a JSON object")
    if message.get("op") != "subscribe":
        raise SubscribeError(f"unsupported op: {message.get('op')!r}")

    missing = [k for k in ("venue", "symbol", "timeframe", "channels") if k not in message]
    if missing:
        raise SubscribeError(f"missing field(s): {', '.join(missing)}")

    channels = message["channels"]
    if not isinstance(channels, list) or not channels:
        raise SubscribeError("channels must be a non-empty list")
    unknown = [c for c in channels if c not in CHANNELS]
    if unknown:
        raise SubscribeError(
            f"unknown channel(s): {', '.join(map(str, unknown))}; "
            f"expected any of {', '.join(sorted(CHANNELS))}"
        )

    return Subscription(
        venue=str(message["venue"]),
        symbol=str(message["symbol"]),
        timeframe=str(message["timeframe"]),
        channels=frozenset(channels),
    )


@dataclass
class Hub:
    """Who is listening to what.

    In-process, like the repository (ADR-019). A deployment with more than one
    worker needs a broker, and that arrives with the storage.
    """

    _subscribers: list[tuple[WebSocket, Subscription]] = field(default_factory=list)

    def subscribe(self, socket: WebSocket, subscription: Subscription) -> None:
        self._subscribers = [(s, sub) for s, sub in self._subscribers if s is not socket]
        self._subscribers.append((socket, subscription))

    def drop(self, socket: WebSocket) -> None:
        self._subscribers = [(s, sub) for s, sub in self._subscribers if s is not socket]

    def recipients(
        self, *, channel: str, venue: str, symbol: str, timeframe: str
    ) -> list[WebSocket]:
        return [
            socket
            for socket, sub in self._subscribers
            if sub.wants(channel=channel, venue=venue, symbol=symbol, timeframe=timeframe)
        ]

    async def publish(
        self,
        *,
        channel: str,
        venue: str,
        symbol: str,
        timeframe: str,
        payload: dict[str, object],
    ) -> int:
        targets = self.recipients(channel=channel, venue=venue, symbol=symbol, timeframe=timeframe)
        for socket in targets:
            await socket.send_json(
                {
                    "channel": channel,
                    "venue": venue,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data": payload,
                }
            )
        return len(targets)


def register_websocket(app: FastAPI) -> None:
    hub = Hub()
    app.state.hub = hub

    @app.websocket("/ws/market")
    async def market(socket: WebSocket) -> None:
        await socket.accept()
        try:
            while True:
                raw = await socket.receive_text()
                try:
                    subscription = parse_subscribe(raw)
                except SubscribeError as exc:
                    # Answered, not fatal: a bad frame is a client bug, and
                    # closing on it turns that into an outage the client cannot
                    # diagnose.
                    await socket.send_json({"ok": False, "error": str(exc)})
                    continue
                hub.subscribe(socket, subscription)
                await socket.send_json(
                    {
                        "ok": True,
                        "subscribed": sorted(subscription.channels),
                        "venue": subscription.venue,
                        "symbol": subscription.symbol,
                        "timeframe": subscription.timeframe,
                    }
                )
        except WebSocketDisconnect:
            hub.drop(socket)
