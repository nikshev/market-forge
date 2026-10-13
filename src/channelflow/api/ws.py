"""PRD section 28.7's live channel.

# @trace: REQ-API-001
# @trace: REQ-WP-102

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

from channelflow.live.messages import LiveBar
from channelflow.live.relay import LiveCache

#: The four PRD section 28.7 names. Anything else is a typo, and a typo that
#: silently subscribed to nothing would look exactly like a quiet market.
CHANNELS = frozenset({"bars", "channel", "features", "signals"})

#: The one timeframe the live feed carries (REQ-WP-102): the ingest's own bars. A subscription at
# another : is accepted and told it is not live, so the page can say so instead of waiting for bars
# that will not come.
LIVE_TIMEFRAME = "1m"

#: Where the browser connects; see `telegram_auth.LIVE_PATH`.
LIVE_PATH = "/api/v1/live"


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
        delivered = 0
        for socket in targets:
            try:
                await socket.send_json(
                    {
                        "channel": channel,
                        "venue": venue,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "data": payload,
                    }
                )
            except Exception:  # noqa: BLE001 -- a socket that went away must not stop the others
                self.drop(socket)
                continue
            delivered += 1
        return delivered

    async def publish_bar(self, bar: LiveBar) -> int:
        """One live 1m bar to whoever subscribed to this series' bars at 1m (REQ-WP-102)."""
        return await self.publish(
            channel="bars",
            venue=bar.venue,
            symbol=bar.symbol,
            timeframe=LIVE_TIMEFRAME,
            payload={"bar": bar.as_wire()},
        )


def register_websocket(app: FastAPI, live: LiveCache | None = None) -> None:
    hub = Hub()
    app.state.hub = hub
    app.state.live_cache = live

    async def market(socket: WebSocket) -> None:
        # A browser that offered the launch-data subprotocol must be answered with one of the names
        # it offered or it drops the connection; the scheme, never the data.
        offered = socket.scope.get("subprotocols", [])
        await socket.accept(subprotocol="tma" if "tma" in offered else None)
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
                live_now = (
                    live is not None
                    and "bars" in subscription.channels
                    and subscription.timeframe == LIVE_TIMEFRAME
                )
                await socket.send_json(
                    {
                        "ok": True,
                        "subscribed": sorted(subscription.channels),
                        "venue": subscription.venue,
                        "symbol": subscription.symbol,
                        "timeframe": subscription.timeframe,
                        "live": live_now,
                    }
                )
                if live_now:
                    assert live is not None
                    # What the table has not caught up on, in one message: even when there is none,
                    # so the page knows it has heard everything before the updates start.
                    await socket.send_json(
                        {
                            "channel": "bars",
                            "venue": subscription.venue,
                            "symbol": subscription.symbol,
                            "timeframe": subscription.timeframe,
                            "data": {
                                "snapshot": [
                                    bar.as_wire()
                                    for bar in live.snapshot(
                                        subscription.venue, subscription.symbol
                                    )
                                ]
                            },
                        }
                    )
        except WebSocketDisconnect:
            hub.drop(socket)

    # PRD section 28.7's route, and the chart's: the second lives under `/api/v1/` so the public
    # proxy's one location reaches it and the Telegram gate can verify launch data on it
    # ([[REQ-WP-102]]).
    app.websocket("/ws/market")(market)
    app.websocket(LIVE_PATH)(market)
