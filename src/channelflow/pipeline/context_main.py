"""The context collector's entrypoint: one process per venue (REQ-WP-093).

# @trace: REQ-WP-093

    python -m channelflow.pipeline.context_main

Reads `CHANNELFLOW_CONTEXT_VENUE` (binance, bybit or okx), polls that venue's public derivatives
endpoints for the symbols `channelflow.context.sources` gives it, and stores each answer in the
`derivatives_state` table. Holds no key: every endpoint is public. Serves `/healthz` and `/metrics`
on `CHANNELFLOW_CONTEXT_PORT`.

One process per venue, as the ingest is one per symbol, for the same reason: a venue that misbehaves
or is rate-limited must not be able to stall another's collection.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from types import FrameType

from channelflow.context import sources
from channelflow.context.pollers import poller_for
from channelflow.context.rest import HttpxJsonClient
from channelflow.context.runtime import Collector, CollectorConfig
from channelflow.context.status import Status, serve
from channelflow.lakehouse import catalog as open_catalog
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import derivatives_state

VENUE = "CHANNELFLOW_CONTEXT_VENUE"
SYMBOLS = "CHANNELFLOW_CONTEXT_SYMBOLS"
PORT = "CHANNELFLOW_CONTEXT_PORT"
LOG_LEVEL = "CHANNELFLOW_LOG_LEVEL"

KNOWN_VENUES = ("binance", "bybit", "okx")
DEFAULT_PORT = 9101


@dataclass(frozen=True)
class ContextSettings:
    venue: str
    symbols: tuple[str, ...]
    port: int


def context_settings_from_env(environ: Mapping[str, str] | None = None) -> ContextSettings:
    values = os.environ if environ is None else environ
    venue = values.get(VENUE, "").strip().lower()
    if not venue:
        raise MissingConfiguration(f"{VENUE} must be set ({', '.join(KNOWN_VENUES)})")
    if venue not in KNOWN_VENUES:
        raise MissingConfiguration(
            f"{VENUE} is {venue!r}; expected one of {', '.join(KNOWN_VENUES)}"
        )

    raw = values.get(SYMBOLS, "").strip()
    symbols = (
        tuple(part.strip() for part in raw.split(",") if part.strip())
        if raw
        else sources.symbols_for(venue)
    )
    if not symbols:
        raise MissingConfiguration(
            f"no symbols for {venue}: {SYMBOLS} is empty and `context.sources` names none"
        )

    raw_port = values.get(PORT, "").strip()
    try:
        port = int(raw_port) if raw_port else DEFAULT_PORT
    except ValueError:
        raise MissingConfiguration(f"{PORT} is {raw_port!r}; expected a port number") from None
    if not 0 < port < 65536:
        raise MissingConfiguration(f"{PORT} is {port}; expected 1-65535")
    return ContextSettings(venue=venue, symbols=symbols, port=port)


def main(argv: list[str] | None = None) -> int:
    level = os.environ.get(LOG_LEVEL, "").strip().upper() or "INFO"
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    context = context_settings_from_env()
    plane = settings_from_env()

    catalog = open_catalog(uri=plane.catalog_uri, warehouse=plane.warehouse, **dict(plane.storage))
    sink = derivatives_state.DerivativesStateSink(derivatives_state.table_for(catalog))
    status = Status(
        venue=context.venue, poll_interval_s=sources.POLL_INTERVAL_S, now_ns=time.time_ns
    )
    collector = Collector(
        config=CollectorConfig(venue=context.venue, symbols=context.symbols),
        poller=poller_for(context.venue, HttpxJsonClient(), time.time_ns),
        sink=sink,
        now_ns=time.time_ns,
        status=status,
    )
    server, _ = serve(status, port=context.port)
    stop = threading.Event()

    def _stop(signum: int, frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    print(
        f"collecting {context.venue} derivatives for {', '.join(context.symbols)} every "
        f"{sources.POLL_INTERVAL_S}s; health on :{context.port}",
        flush=True,
    )
    try:
        collector.run(stop)
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
