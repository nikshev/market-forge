"""Starts the live relay with the API and ties it to the WebSocket hub (REQ-WP-102).

# @trace: REQ-WP-102

The relay runs in a thread of its own (a Kafka poll blocks), and each bar it forwards is handed to
the hub on the server's event loop. It starts and stops with the application, and a broker that is
not there is not a reason the API will not start: the page says the chart is delayed.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable

from fastapi import FastAPI

from channelflow.live.messages import LiveBar
from channelflow.live.relay import LiveCache, LiveRelay
from channelflow.transport import EventConsumer

logger = logging.getLogger(__name__)


def attach_live(
    app: FastAPI,
    cache: LiveCache,
    make_consumers: Callable[[], tuple[EventConsumer, EventConsumer | None]],
) -> None:
    """Run a relay for the lifetime of `app`, filling `cache` and forwarding to its hub."""
    state: dict[str, object] = {}

    async def start() -> None:
        loop = asyncio.get_running_loop()
        hub = app.state.hub

        def forward(bar: LiveBar) -> None:
            asyncio.run_coroutine_threadsafe(hub.publish_bar(bar), loop)

        def run() -> None:
            try:
                finals, forming = make_consumers()
                relay = LiveRelay(finals, cache, forward, tail=forming)
            except Exception:  # noqa: BLE001 -- no broker is not a reason not to serve
                logger.exception("live feed: could not start; the chart will say it is delayed")
                return
            state["relay"] = relay
            app.state.live_relay = relay
            relay.run(stop)

        stop = threading.Event()
        thread = threading.Thread(target=run, name="live-relay", daemon=True)
        state["stop"], state["thread"] = stop, thread
        thread.start()

    async def shutdown() -> None:
        stop = state.get("stop")
        if isinstance(stop, threading.Event):
            stop.set()

    app.router.add_event_handler("startup", start)
    app.router.add_event_handler("shutdown", shutdown)
