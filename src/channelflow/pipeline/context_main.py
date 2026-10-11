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
from channelflow.context.liquidations import liquidation_task
from channelflow.context.pollers import OkxPoller, poller_for
from channelflow.context.rest import HttpxJsonClient
from channelflow.context.runtime import Collector, CollectorConfig, Flushable
from channelflow.context.status import Status, serve
from channelflow.lakehouse import catalog as open_catalog
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import derivatives_state
from channelflow.tables import liquidations as liquidation_table

VENUE = "CHANNELFLOW_CONTEXT_VENUE"
SYMBOLS = "CHANNELFLOW_CONTEXT_SYMBOLS"
PORT = "CHANNELFLOW_CONTEXT_PORT"
STREAMS = "CHANNELFLOW_CONTEXT_STREAMS"
LOG_LEVEL = "CHANNELFLOW_LOG_LEVEL"

KNOWN_VENUES = ("binance", "bybit", "okx")
#: The websocket streams a collector can run beside its polls; each is its own requirement.
KNOWN_STREAMS = ("liquidations",)
DEFAULT_STREAMS: tuple[str, ...] = ("liquidations",)
DEFAULT_PORT = 9101


@dataclass(frozen=True)
class ContextSettings:
    venue: str
    symbols: tuple[str, ...]
    port: int
    streams: tuple[str, ...] = DEFAULT_STREAMS


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
    raw_streams = values.get(STREAMS)
    if raw_streams is None:
        streams = DEFAULT_STREAMS
    else:
        streams = tuple(part.strip().lower() for part in raw_streams.split(",") if part.strip())
        unknown = [name for name in streams if name not in KNOWN_STREAMS]
        if unknown:
            raise MissingConfiguration(
                f"{STREAMS} names {', '.join(unknown)}; expected any of {', '.join(KNOWN_STREAMS)}"
            )
    return ContextSettings(venue=venue, symbols=symbols, port=port, streams=streams)


def main(argv: list[str] | None = None) -> int:
    level = os.environ.get(LOG_LEVEL, "").strip().upper() or "INFO"
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs every request at INFO: nine lines a minute that say nothing a failure does not.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    context = context_settings_from_env()
    plane = settings_from_env()

    catalog = open_catalog(uri=plane.catalog_uri, warehouse=plane.warehouse, **dict(plane.storage))
    sink = derivatives_state.DerivativesStateSink(derivatives_state.table_for(catalog))
    status = Status(
        venue=context.venue, poll_interval_s=sources.POLL_INTERVAL_S, now_ns=time.time_ns
    )
    poller = poller_for(context.venue, HttpxJsonClient(), time.time_ns)
    streams = []
    extra_sinks: list[Flushable] = []
    if "liquidations" in context.streams:
        liquidation_sink = liquidation_table.LiquidationSink(liquidation_table.table_for(catalog))
        contract_values = (
            {symbol: poller.contract_value(symbol) for symbol in context.symbols}
            if isinstance(poller, OkxPoller)
            else {}
        )
        task = liquidation_task(
            venue=context.venue,
            symbols=context.symbols,
            sink=liquidation_sink,
            now_ns=time.time_ns,
            on_failure=lambda message: status.record_failure("liquidation-stream"),
            contract_values=contract_values,
        )
        try:
            task.start()
        except Exception as error:  # noqa: BLE001 -- the session reconnects; a poll must still run
            logging.getLogger(__name__).error(
                "%s: liquidation stream did not connect at start (%s: %s); the session will retry",
                context.venue,
                type(error).__name__,
                error,
            )
        streams.append(task)
        extra_sinks.append(liquidation_sink)
    collector = Collector(
        config=CollectorConfig(venue=context.venue, symbols=context.symbols),
        poller=poller,
        sink=sink,
        now_ns=time.time_ns,
        status=status,
        streams=tuple(streams),
        extra_sinks=tuple(extra_sinks),
    )
    server, _ = serve(status, port=context.port)
    stop = threading.Event()

    def _stop(signum: int, frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    print(
        f"collecting {context.venue} derivatives for {', '.join(context.symbols)} every "
        f"{sources.POLL_INTERVAL_S}s (streams: {', '.join(context.streams) or 'none'}); "
        f"health on :{context.port}",
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
