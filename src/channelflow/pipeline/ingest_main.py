"""How the ingest daemon starts.

# @trace: REQ-WP-066
# @trace: REQ-WP-076

The same shape as the read API's composition root, and for the same reasons: the
environment is the only input, nothing defaults, and a missing variable refuses
to start rather than filling an empty warehouse that reads as a quiet market.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import StreamSession
from channelflow.connectors.venue import (
    VENUE_REGISTRY,
    bybit_subscribe_message,
    okx_subscribe_message,
)
from channelflow.connectors.websocket import binance_stream_url
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore, ObjectStore, S3ObjectStore
from channelflow.pipeline.ingest import IngestDaemon
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import bars as bars_table

SYMBOLS = "CHANNELFLOW_INGEST_SYMBOLS"
ARCHIVE_URI = "CHANNELFLOW_ARCHIVE_URI"
TIMEFRAME = "CHANNELFLOW_INGEST_TIMEFRAME_NS"
INGEST_VENUE = "CHANNELFLOW_INGEST_VENUE"
SILENCE_WINDOW_MULTIPLIER = "CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER"

#: One minute. A chart shows its first candle a minute after the daemon starts
#: rather than fifteen, which is the difference between believing it works and
#: waiting to find out.
DEFAULT_TIMEFRAME_NS = 60_000_000_000
DEFAULT_SILENCE_WINDOW_MULTIPLIER = 2.0

SYMBOLS_BYBIT = "CHANNELFLOW_INGEST_SYMBOLS_BYBIT"
SYMBOLS_OKX = "CHANNELFLOW_INGEST_SYMBOLS_OKX"


class SystemClock:
    """`StreamSession`'s clock, against the real one."""

    def now_ns(self) -> int:
        import time

        return time.time_ns()


@dataclass(frozen=True)
class IngestSettings:
    symbols: tuple[str, ...]
    archive_uri: str
    timeframe_ns: int
    silence_window_multiplier: float


def ingest_settings_from_env(environ: Mapping[str, str] | None = None) -> IngestSettings:
    values = os.environ if environ is None else environ

    missing = [name for name in (SYMBOLS, ARCHIVE_URI) if not values.get(name, "").strip()]
    if missing:
        raise MissingConfiguration(
            f"{', '.join(missing)} must be set; a daemon with no symbols reads nothing "
            "and one with no archive keeps nothing, and both look like a quiet venue"
        )

    symbols = tuple(part.strip() for part in values[SYMBOLS].split(",") if part.strip())
    if not symbols:
        raise MissingConfiguration(f"{SYMBOLS} named no symbol")

    raw_timeframe = values.get(TIMEFRAME, "").strip()
    timeframe = int(raw_timeframe) if raw_timeframe else DEFAULT_TIMEFRAME_NS
    if timeframe <= 0:
        raise MissingConfiguration(f"{TIMEFRAME} must be positive, got {timeframe}")

    raw_silence = values.get(SILENCE_WINDOW_MULTIPLIER, "").strip()
    silence_window = float(raw_silence) if raw_silence else DEFAULT_SILENCE_WINDOW_MULTIPLIER
    if silence_window <= 0:
        raise MissingConfiguration(
            f"{SILENCE_WINDOW_MULTIPLIER} must be positive, got {silence_window}"
        )

    return IngestSettings(
        symbols=symbols,
        archive_uri=values[ARCHIVE_URI].strip(),
        timeframe_ns=timeframe,
        silence_window_multiplier=silence_window,
    )


def object_store_for(uri: str, storage: Mapping[str, str]) -> ObjectStore:
    """`s3://bucket/...` or a directory. One seam, two implementations.

    The scheme decides, and nothing else does: the same line `lakehouse.catalog`
    draws between a local run and a deployment.
    """
    if not uri.startswith("s3://"):
        return LocalObjectStore(root=Path(uri))

    import boto3

    bucket = uri.removeprefix("s3://").split("/", 1)[0]
    client = boto3.client(
        "s3",
        endpoint_url=storage.get("s3.endpoint"),
        aws_access_key_id=storage.get("s3.access-key-id"),
        aws_secret_access_key=storage.get("s3.secret-access-key"),
        region_name=storage.get("s3.region"),
    )
    return S3ObjectStore(bucket=bucket, client=client)


def _resolve_connector(dotted: str) -> Any:
    """Import the connector class the registry names.

    The registry stores a dotted path rather than the class so importing the
    registry does not import every venue's dependencies. The return is `Any`
    deliberately: the three venues take different constructor arguments, so no
    single signature describes them, and a path that names something else fails
    loudly at startup, where a refusal to start is the documented behaviour.
    """
    module_name, _, class_name = dotted.rpartition(".")
    return getattr(import_module(module_name), class_name)


def _connector_for_venue(venue: str) -> tuple[str, str]:
    """Build the connector and subscribe message for a venue."""
    config = VENUE_REGISTRY[venue]
    streams = config.stream_builder(["placeholder"])  # will be replaced with actual symbols
    subscribe_msg = ""
    if venue == "bybit":
        subscribe_msg = bybit_subscribe_message(streams)
    elif venue == "okx":
        subscribe_msg = okx_subscribe_message(streams)
    # For binance, subscribe_msg is empty (uses URL params).
    # The registry already holds the dotted path; nothing to compose.
    return config.connector, subscribe_msg


def build_daemon(
    *,
    symbol: str,
    settings: IngestSettings,
    store: ObjectStore,
    catalog_uri: str,
    warehouse: str,
    storage: Mapping[str, str],
    venue: str,
) -> IngestDaemon:
    """One symbol's daemon, wired from configuration."""
    if venue not in VENUE_REGISTRY:
        raise MissingConfiguration(f"Unknown venue: {venue}. Known: {list(VENUE_REGISTRY.keys())}")

    config = VENUE_REGISTRY[venue]
    catalog = open_catalog(uri=catalog_uri, warehouse=warehouse, **dict(storage))
    sink = bars_table.BarSink(table=bars_table.table_for(catalog))
    builder = BarBuilder(timeframe_ns=settings.timeframe_ns, on_final=sink)

    streams = config.stream_builder([symbol])
    connector_cls = _resolve_connector(config.connector)

    if venue == "binance":
        connector = connector_cls(url_for=binance_stream_url)
    elif venue == "bybit":
        connector = connector_cls(
            url="wss://stream.bybit.com/v5/public/linear",
            subscribe_msg=bybit_subscribe_message(streams),
        )
    elif venue == "okx":
        connector = connector_cls(
            url="wss://ws.okx.com:8443/api/v5/market",
            subscribe_msg=okx_subscribe_message(streams),
        )
    else:
        raise MissingConfiguration(f"Unsupported venue: {venue}")

    session = StreamSession(
        streams=streams, policy=config.policy, connector=connector, clock=SystemClock()
    )
    prefix = settings.archive_uri.removeprefix("s3://").split("/", 1)
    return IngestDaemon(
        session=session,
        connector=connector,
        archive=FrameArchive(
            store=store,
            venue=venue,
            prefix=f"{venue}/{prefix[1] if len(prefix) > 1 else 'raw/cex'}",
        ),
        builder=builder,
        venue=venue,
        flush_bars=sink.flush,
        bars_pending=lambda: sink.pending,
        now_ns=lambda: time.time_ns(),
        silence_window_multiplier=settings.silence_window_multiplier,
    )


def main(argv: list[str] | None = None) -> int:
    plane = settings_from_env()
    ingest = ingest_settings_from_env()

    if not os.environ.get(INGEST_VENUE, "").strip():
        raise MissingConfiguration(f"{INGEST_VENUE} must be set (binance, bybit, or okx)")

    venue = os.environ[INGEST_VENUE].strip().lower()

    if len(ingest.symbols) > 1:
        # One process per symbol, deliberately. `BarBuilder` is one symbol and
        # one timeframe, and a daemon multiplexing several would own a decision
        # a deployment can make better -- and would share one socket's failure
        # across all of them.
        raise MissingConfiguration(
            f"{SYMBOLS} names {len(ingest.symbols)} symbols; run one process each"
        )

    store = object_store_for(ingest.archive_uri, plane.storage)
    daemon = build_daemon(
        symbol=ingest.symbols[0],
        settings=ingest,
        store=store,
        catalog_uri=plane.catalog_uri,
        warehouse=plane.warehouse,
        storage=plane.storage,
        venue=venue,
    )
    print(
        f"ingesting {ingest.symbols[0]} at {ingest.timeframe_ns / 1e9:g}s bars for {venue}, "
        f"archiving to {ingest.archive_uri}"
    )
    daemon.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
